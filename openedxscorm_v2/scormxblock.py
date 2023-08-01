import json
import hashlib
import os
import logging
import re
import xml.etree.ElementTree as ET
import zipfile

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.template import Context, Template
from django.utils import timezone
from django.utils.module_loading import import_string
from webob import Response
import pkg_resources
from six import string_types

from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.completable import CompletableXBlockMixin
from xblock.fields import Scope, String, Float, Boolean, Dict, DateTime, Integer

from xmodule.contentstore.django import contentstore


# Make '_' a no-op so we can scrape strings
def _(text):
    return text


logger = logging.getLogger(__name__)


@XBlock.wants("settings")
class ScormXBlock(XBlock, CompletableXBlockMixin):
    """
    When a user uploads a Scorm package, the zip file is stored in:

        media/{org}/{course}/{block_type}/{block_id}/{sha1}{ext}

    This zip file is then extracted to the media/{scorm_location}/{block_id}.

    The scorm location is defined by the LOCATION xblock setting. If undefined, this is
    "scorm". This setting can be set e.g:

        XBLOCK_SETTINGS["ScormXBlock"] = {
            "LOCATION": "alternatevalue",
        }

    Note that neither the folder the folder nor the package file are deleted when the
    xblock is removed.

    By default, static assets are stored in the default Django storage backend. To
    override this behaviour, you should define a custom storage function. This
    function must take the xblock instance as its first and only argument. For instance,
    you can store assets in different directories depending on the XBlock organisation with::

        def scorm_storage(xblock):
            from django.conf import settings
            from django.core.files.storage import FileSystemStorage
            from openedx.core.djangoapps.site_configuration.models import SiteConfiguration

            subfolder = SiteConfiguration.get_value_for_org(
                xblock.location.org, "SCORM_STORAGE_NAME", "default"
            )
            storage_location = os.path.join(settings.MEDIA_ROOT, subfolder)
            return get_storage_class(settings.DEFAULT_FILE_STORAGE)(location=storage_location)

        XBLOCK_SETTINGS["ScormXBlock"] = {
            "STORAGE_FUNC": scorm_storage,
        }
    """

    display_name = String(
        display_name=_("Display Name"),
        help=_("Display name for this module"),
        default="Scorm module v2",
        scope=Scope.settings,
    )
    scorm_file = String(
        display_name=_("SCORM file package"),
        help=_(
            'Name of the SCORM Zip file uploaded through the "Files & Uploads" section of the Course.  Only ".zip" files allowed.'
        ),
        default="",
        scope=Scope.settings,
    )
    index_page_path = String(
        display_name=_("Path to the index page in scorm file"), scope=Scope.settings
    )
    package_meta = Dict(scope=Scope.content)
    scorm_version = String(default="SCORM_12", scope=Scope.settings)

    # lesson_status is for SCORM 1.2 and can take the following values:
    # "passed", "completed", "failed", "incomplete", "browsed", "not attempted"
    # In SCORM_2004, status is broken down in two elements:
    # - cmi.completion_status: "completed" vs "incomplete"
    # - cmi.success_status: "passed" vs "failed"
    # We denormalize these two elements by storing the completion status in self.lesson_status.
    lesson_status = String(scope=Scope.user_state, default="not attempted")
    success_status = String(scope=Scope.user_state, default="unknown")

    lesson_score = Float(scope=Scope.user_state, default=0)
    weight = Float(
        default=1,
        display_name=_("Weight"),
        help=_("Weight/Maximum grade"),
        scope=Scope.settings,
    )
    has_score = Boolean(
        display_name=_("Scored"),
        help=_(
            "Select False if this component will not receive a numerical score from the Scorm"
        ),
        default=True,
        scope=Scope.settings,
    )

    # See the Scorm data model:
    # https://scorm.com/scorm-explained/technical-scorm/run-time/
    scorm_data = Dict(scope=Scope.user_state, default={})

    icon_class = String(default="video", scope=Scope.settings)
    width = Integer(
        display_name=_("Display width (px)"),
        help=_("Width of iframe (default: 100%)"),
        scope=Scope.settings,
    )
    height = Integer(
        display_name=_("Display height (px)"),
        help=_("Height of iframe"),
        default=450,
        scope=Scope.settings,
    )

    fullscreen_on_launch = Boolean(
        display_name=_("Fullscreen on launch"),
        help=_("Display in fullscreen mode on launch"),
        default=False,
        scope=Scope.settings,
    )

    has_author_view = True

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

    @staticmethod
    def resource_string(path):
        """Handy helper for getting static resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def author_view(self, context=None):
        context = context or {}
        if not self.index_page_path:
            context[
                "message"
            ] = "Click 'Edit' to modify this module and upload a new SCORM package."
        return self.student_view(context=context, is_author=True);

    def student_view(self, context=None, is_author=False):
        self._get_package_file_and_extract()

        student_context = {
            "index_page_url": self.index_page_url,
            "completion_status": self.lesson_status,
            "grade": self.get_grade(),
            "scorm_xblock": self,
        }
        student_context.update(context or {})
        if is_author: 
            template = self.render_template("static/html/scormstudioxblock.html", student_context)
        else: 
            template = self.render_template("static/html/scormxblock.html", student_context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/scormxblock.css"))
        frag.add_javascript(self.resource_string("static/js/src/scormxblock.js"))
        frag.initialize_js(
            "ScormXBlock",
            json_args={
                "scorm_version": self.scorm_version,
                "fullscreen_on_launch": self.fullscreen_on_launch,
                "scorm_data": self.scorm_data,
            },
        )
        return frag

    def studio_view(self, context=None):
        # Note that we cannot use xblockutils's StudioEditableXBlockMixin because we
        # need to support package file uploads.
        self._get_package_file_and_extract()

        studio_context = {
            "field_display_name": self.fields["display_name"],
            "field_scorm_file": self.fields["scorm_file"],
            "field_has_score": self.fields["has_score"],
            "field_weight": self.fields["weight"],
            "field_width": self.fields["width"],
            "field_height": self.fields["height"],
            "field_fullscreen_on_launch": self.fields["fullscreen_on_launch"],
            "scorm_xblock": self,
        }
        studio_context.update(context or {})
        template = self.render_template("static/html/studio.html", studio_context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/scormxblock.css"))
        frag.add_javascript(self.resource_string("static/js/src/studio.js"))
        frag.initialize_js("ScormStudioXBlock")
        return frag

    @staticmethod
    def json_response(data):
        return Response(
            json.dumps(data), content_type="application/json", charset="utf8"
        )

    @XBlock.handler
    def studio_submit(self, request, _suffix):
        self.display_name = request.params["display_name"]
        self.width = parse_int(request.params["width"], None)
        self.height = parse_int(request.params["height"], None)
        self.has_score = request.params["has_score"] == "1"
        self.weight = parse_float(request.params["weight"], 1)
        self.fullscreen_on_launch = request.params["fullscreen_on_launch"] == "1"
        self.icon_class = "problem" if self.has_score else "video"
        self.scorm_file = request.params.get("scorm_file")

        response = {"result": "success", "errors": []}
        
        if not self.scorm_file:
            # File not uploaded
            return self.json_response(response)

        try:
            package_file = self._get_package_file()
        except Exception:
            response["errors"].append("SCORM package not found. Make sure the name is correct and the file type is '.zip' ")
            return self.json_response(response)

        self.update_package_meta(package_file)

        # Clean storage folder, if it already exists
        self.clean_storage()

        # Extract zip file
        try:
            self.extract_package(package_file)
            self.update_package_fields()
        except ScormError as e:
            response["errors"].append(e.args[0])

        return self.json_response(response)

    # This function has been borrowed from Abstract-Tech
    # https://github.com/Abstract-Tech/abstract-scorm-xblock/blob/11c2f0ec61dbc4d4e1af37b5a203c2f8be7eb944/abstract_scorm_xblock/abstract_scorm_xblock/scormxblock.py#L319
    def _search_scorm_package(self):
        """
        Search the mongo contentstore for the filename and return the file metadata
        """
        scorm_content, count = contentstore().get_all_content_for_course(
            self.runtime.course_id,
            filter_params={
                "contentType": {
                    "$in": ["application/zip", "application/x-zip-compressed"]
                },
                "displayname": self.scorm_file,
            },
        )
        if not count:
            raise Exception(
                'SCORM package "{}" not found'.format(self.scorm_file)
            )
        # Since course content names are unique we are sure that we
        # can't have multiple results, so we just pop the first.
        return scorm_content.pop()

    def _get_package_file_and_extract(self):
        """
        If the SCORM package is not already extracted, then
        get and extract the SCORM package
        """
        # Check if the `package_meta` has `sha1` key to make sure
        # if the package name is not empty
        if "sha1" in self.package_meta and not self.storage.exists(self.extract_folder_path):
            logger.info(
                'SCORM package is not extracted in "%s". Extracting it now.', self.extract_folder_path
            )
            try:
                package_file = self._get_package_file()
                self.extract_package(package_file)
            except Exception as e:
                logger.warning(e)
    
    def _get_package_file(self):
        """
        Convert the file content (in bytes) to a ContentFile and return it 
        """
        scorm_package = self._search_scorm_package()
        # We are actually loading the whole zipfile in memory.
        # This step should probably be handled more carefully.

        # Code snippet borrowed from
        # https://github.com/Abstract-Tech/abstract-scorm-xblock/blob/11c2f0ec61dbc4d4e1af37b5a203c2f8be7eb944/abstract_scorm_xblock/abstract_scorm_xblock/scormxblock.py#L343
        scorm_zipfile_data = contentstore().find(scorm_package["asset_key"]).data

        return ContentFile(scorm_zipfile_data)

    def clean_storage(self):
        if self.storage.exists(self.extract_folder_base_path):
            logger.info(
                'Removing previously unzipped "%s"', self.extract_folder_base_path
            )
            self.recursive_delete(self.extract_folder_base_path)

    def recursive_delete(self, root):
        """
        Recursively delete the contents of a directory in the Django default storage.
        Unfortunately, this will not delete empty folders, as the default FileSystemStorage
        implementation does not allow it.
        """
        directories, files = self.storage.listdir(root)
        for directory in directories:
            self.recursive_delete(os.path.join(root, directory))
        for f in files:
            self.storage.delete(os.path.join(root, f))

    def extract_package(self, package_file):
        with zipfile.ZipFile(package_file, "r") as scorm_zipfile:
            zipinfos = scorm_zipfile.infolist()
            root_path = None
            root_depth = -1
            # Find root folder which contains imsmanifest.xml
            for zipinfo in zipinfos:
                if os.path.basename(zipinfo.filename) == "imsmanifest.xml":
                    depth = len(os.path.split(zipinfo.filename))
                    if depth < root_depth or root_depth < 0:
                        root_path = os.path.dirname(zipinfo.filename)
                        root_depth = depth

            if root_path is None:
                raise ScormError(
                    "Could not find 'imsmanifest.xml' file in the scorm package"
                )

            for zipinfo in zipinfos:
                # Extract only files that are below the root
                if zipinfo.filename.startswith(root_path):
                    # Do not unzip folders, only files. In Python 3.6 we will have access to
                    # the is_dir() method to verify whether a ZipInfo object points to a
                    # directory.
                    # https://docs.python.org/3.6/library/zipfile.html#zipfile.ZipInfo.is_dir
                    if not zipinfo.filename.endswith("/"):
                        dest_path = os.path.join(
                            self.extract_folder_path,
                            os.path.relpath(zipinfo.filename, root_path),
                        )
                        self.storage.save(
                            dest_path,
                            ContentFile(scorm_zipfile.read(zipinfo.filename)),
                        )

    @property
    def index_page_url(self):
        if not self.package_meta or not self.index_page_path:
            return ""
        folder = self.extract_folder_path
        if self.storage.exists(
            os.path.join(self.extract_folder_base_path, self.index_page_path)
        ):
            # For backward-compatibility, we must handle the case when the xblock data
            # is stored in the base folder.
            folder = self.extract_folder_base_path
            logger.warning("Serving SCORM content from old-style path: %s", folder)
        return self.storage.url(os.path.join(folder, self.index_page_path))

    @property
    def extract_folder_path(self):
        """
        This path needs to depend on the content of the scorm package. Otherwise,
        served media files might become stale when the package is update.
        """
        return os.path.join(self.extract_folder_base_path, self.package_meta["sha1"])

    @property
    def extract_folder_base_path(self):
        """
        Path to the folder where packages will be extracted.
        """
        return os.path.join(self.scorm_location(), self.location.block_id)

    @XBlock.json_handler
    def scorm_get_value(self, data, _suffix):
        """
        Here we get only the get_value events that were not filtered by the LMSGetValue js function.
        """
        name = data.get("name")
        if name in ["cmi.core.lesson_status", "cmi.completion_status"]:
            return {"value": self.lesson_status}
        if name == "cmi.success_status":
            return {"value": self.success_status}
        if name in ["cmi.core.score.raw", "cmi.score.raw"]:
            return {"value": self.lesson_score * 100}
        return {"value": self.scorm_data.get(name, "")}

    @XBlock.json_handler
    def scorm_set_values(self, data_list, _suffix):
        return [self.set_value(data) for data in data_list]

    @XBlock.json_handler
    def scorm_set_value(self, data, _suffix):
        return self.set_value(data)

    def set_value(self, data):
        name = data.get("name")
        completion_percent = None
        success_status = None
        completion_status = None
        lesson_score = None

        if name == "cmi.core.lesson_status":
            lesson_status = data.get("value")
            if lesson_status in ["passed", "failed"]:
                success_status = lesson_status
            elif lesson_status in ["completed", "incomplete"]:
                completion_status = lesson_status
        elif name == "cmi.success_status":
            success_status = data.get("value")
        elif name == "cmi.completion_status":
            completion_status = data.get("value")
        elif name in ["cmi.core.score.raw", "cmi.score.raw"] and self.has_score:
            lesson_score = float(data.get("value", 0)) / 100.0
        elif name == "cmi.progress_measure":
            try:
                completion_percent = float(data.get("value"))
            except (ValueError, TypeError):
                pass
        else:
            self.scorm_data[name] = data.get("value", "")

        context = {"result": "success"}
        if lesson_score is not None:
            self.lesson_score = lesson_score
            context.update({"grade": self.get_grade()})
        # Code commented out as this call marks the unit as completed even if completion_percent < 1
        # if completion_percent is not None:
            # self.emit_completion(completion_percent)
        if completion_status:
            self.lesson_status = completion_status
            context.update({"completion_status": completion_status})
        if success_status:
            self.success_status = success_status
        if success_status == "passed" or completion_status == "completed":
            self.publish_completion()
            if self.has_score:
                self.publish_grade()

        return context
    
    def publish_completion(self):
        """
        Utility method used to mark a vertical block as complete.
        """
        completion_percent = 1.0
        self.emit_completion(completion_percent)

    def publish_grade(self):
        self.runtime.publish(
            self,
            "grade",
            {"value": self.get_grade(), "max_value": self.weight},
        )

    def get_grade(self):
        lesson_score = 0 if self.is_failed else self.lesson_score

        """
        We expect the scorm events to be published in the
        following order

        ```
        score
        completion_status
        ```

        but some SCORM packages publish the completion_status
        first followed by score
        
        ```
        completion_status
        score
        ```

        Since the grading is needed for Open edX to mark the
        course as complete, we hard coded the score to 1
        this score is only used by Open edX and it won't affect
        the digital credentials score
        """
        if lesson_score == 0:
            lesson_score = 1

        return lesson_score * self.weight

    @property
    def is_failed(self):
        return self.success_status == "failed"

    def set_score(self, score):
        """
        Utility method used to rescore a problem.
        """
        self.lesson_score = score.raw_earned / self.weight

    def max_score(self):
        """
        Return the maximum score possible.
        """
        return self.weight if self.has_score else None

    def update_package_meta(self, package_file):
        self.package_meta["sha1"] = self.get_sha1(package_file)
        self.package_meta["name"] = package_file.name
        self.package_meta["last_updated"] = timezone.now().strftime(
            DateTime.DATETIME_FORMAT
        )
        self.package_meta["size"] = package_file.seek(0, 2)
        package_file.seek(0)

    def update_package_fields(self):
        """
        Update version and index page path fields.
        """
        imsmanifest_path = self.find_file_path("imsmanifest.xml")
        imsmanifest_file = self.storage.open(imsmanifest_path)
        tree = ET.parse(imsmanifest_file)
        imsmanifest_file.seek(0)
        namespace = ""
        for _, node in ET.iterparse(imsmanifest_file, events=["start-ns"]):
            if node[0] == "":
                namespace = node[1]
                break
        root = tree.getroot()

        prefix = "{" + namespace + "}" if namespace else ""
        resource = root.find(
            "{prefix}resources/{prefix}resource[@href]".format(prefix=prefix)
        )
        schemaversion = root.find(
            "{prefix}metadata/{prefix}schemaversion".format(prefix=prefix)
        )

        if resource is not None:
            self.index_page_path = resource.get("href")
        else:
            self.index_page_path = self.find_relative_file_path("index.html")
        if (schemaversion is not None) and (
            re.match("^1.2$", schemaversion.text) is None
        ):
            self.scorm_version = "SCORM_2004"
        else:
            self.scorm_version = "SCORM_12"

    def find_relative_file_path(self, filename):
        return os.path.relpath(self.find_file_path(filename), self.extract_folder_path)

    def find_file_path(self, filename):
        """
        Search recursively in the extracted folder for a given file. Path of the first
        found file will be returned. Raise a ScormError if file cannot be found.
        """
        path = self.get_file_path(filename, self.extract_folder_path)
        if path is None:
            raise ScormError(
                "Invalid package: could not find '{}' file".format(filename)
            )
        return path

    def get_file_path(self, filename, root):
        """
        Same as `find_file_path`, but don't raise error on file not found.
        """
        subfolders, files = self.storage.listdir(root)
        for f in files:
            if f == filename:
                return os.path.join(root, filename)
        for subfolder in subfolders:
            path = self.get_file_path(filename, os.path.join(root, subfolder))
            if path is not None:
                return path
        return None

    def scorm_location(self):
        """
        Unzipped files will be stored in a media folder with this name, and thus
        accessible at a url with that also includes this name.
        """
        default_scorm_location = "scorm"
        return self.xblock_settings.get("LOCATION", default_scorm_location)

    @staticmethod
    def get_sha1(file_descriptor):
        """
        Get file hex digest (fingerprint).
        """
        block_size = 8 * 1024
        sha1 = hashlib.sha1()
        while True:
            block = file_descriptor.read(block_size)
            if not block:
                break
            sha1.update(block)
        file_descriptor.seek(0)
        return sha1.hexdigest()

    def student_view_data(self):
        """
        Inform REST api clients about original file location and it's "freshness".
        Make sure to include `student_view_data=openedxscorm` to URL params in the request.

        Note: we are not sure what this view is for and it might be removed in the future.
        """
        self._get_package_file_and_extract()

        if self.index_page_url:
            return {
                "last_modified": self.package_meta.get("last_updated", ""),
                "size": self.package_meta.get("size", 0),
                "index_page": self.index_page_path,
            }
        return {}

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            (
                "ScormXBlock",
                """<vertical_demo>
                <openedxscorm/>
                </vertical_demo>
             """,
            ),
        ]

    @property
    def storage(self):
        """
        Return the storage backend used to store the assets of this xblock. This is a cached property.
        """
        if not getattr(self, "_storage", None):

            def get_default_storage(_xblock):
                return default_storage

            storage_func = self.xblock_settings.get("STORAGE_FUNC", get_default_storage)
            if isinstance(storage_func, string_types):
                storage_func = import_string(storage_func)
            self._storage = storage_func(self)

        return self._storage

    @property
    def xblock_settings(self):
        """
        Return a dict of settings associated to this XBlock.
        """
        settings_service = self.runtime.service(self, "settings") or {}
        if not settings_service:
            return {}
        return settings_service.get_settings_bucket(self)


def parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class ScormError(Exception):
    pass
