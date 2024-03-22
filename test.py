bl_info = {
    "name": "DD FBX Importer",
    "author": "Yu-Lit",
    "version": (0, 0, 1),
    "blender": (4, 1, 0),
    "location": "",
    "description": "",
    "warning": "",
    "support": "COMMUNITY",
    "doc_url": "",
    "tracker_url": "",
    "category": "",
}


if "bpy" in locals():
    import importlib

    reloadable_modules = [
        "preparation_logger",
        "debug",
    ]

    for module in reloadable_modules:
        if module in locals():
            importlib.reload(locals()[module])

else:
    from .Logging import preparation_logger
    from . import debug


import bpy
import mathutils

from bpy_extras.io_utils import orientation_helper

from .debug import (
    launch_debug_server,
)


"""---------------------------------------------------------
------------------------------------------------------------
    Logger
------------------------------------------------------------
---------------------------------------------------------"""
from .Logging.preparation_logger import preparating_logger

logger = preparating_logger(__name__)


"""---------------------------------------------------------
------------------------------------------------------------
    Property Group
------------------------------------------------------------
---------------------------------------------------------"""


"""---------------------------------------------------------
------------------------------------------------------------
    Operator
------------------------------------------------------------
---------------------------------------------------------"""


@orientation_helper(axis_forward="-Z", axis_up="Y")
class BuiltInFBXImporterBase(bpy.types.Operator):

    filename_ext = ".fbx"
    filter_glob: bpy.props.StringProperty(default="*.fbx", options={"HIDDEN"})

    ui_tab: bpy.props.EnumProperty(
        items=(
            ("MAIN", "Main", "Main basic settings"),
            ("ARMATURE", "Armatures", "Armature-related settings"),
        ),
        name="ui_tab",
        description="Import options categories",
    )

    use_manual_orientation: bpy.props.BoolProperty(
        name="Manual Orientation",
        description="Specify orientation and scale, instead of using embedded data in FBX file",
        default=False,
    )
    global_scale: bpy.props.FloatProperty(
        name="Scale",
        min=0.001,
        max=1000.0,
        default=1.0,
    )
    bake_space_transform: bpy.props.BoolProperty(
        name="Apply Transform",
        description="Bake space transform into object data, avoids getting unwanted rotations to objects when "
        "target space is not aligned with Blender's space "
        "(WARNING! experimental option, use at own risk, known to be broken with armatures/animations)",
        default=False,
    )

    use_custom_normals: bpy.props.BoolProperty(
        name="Custom Normals",
        description="Import custom normals, if available (otherwise Blender will recompute them)",
        default=True,
    )
    colors_type: bpy.props.EnumProperty(
        name="Vertex Colors",
        items=(
            ("NONE", "None", "Do not import color attributes"),
            ("SRGB", "sRGB", "Expect file colors in sRGB color space"),
            ("LINEAR", "Linear", "Expect file colors in linear color space"),
        ),
        description="Import vertex color attributes",
        default="SRGB",
    )

    use_image_search: bpy.props.BoolProperty(
        name="Image Search",
        description="Search subdirs for any associated images (WARNING: may be slow)",
        default=True,
    )

    use_alpha_decals: bpy.props.BoolProperty(
        name="Alpha Decals",
        description="Treat materials with alpha as decals (no shadow casting)",
        default=False,
    )
    decal_offset: bpy.props.FloatProperty(
        name="Decal Offset",
        description="Displace geometry of alpha meshes",
        min=0.0,
        max=1.0,
        default=0.0,
    )

    use_anim: bpy.props.BoolProperty(
        name="Import Animation",
        description="Import FBX animation",
        default=True,
    )
    anim_offset: bpy.props.FloatProperty(
        name="Animation Offset",
        description="Offset to apply to animation during import, in frames",
        default=1.0,
    )

    use_subsurf: bpy.props.BoolProperty(
        name="Subdivision Data",
        description="Import FBX subdivision information as subdivision surface modifiers",
        default=False,
    )

    use_custom_props: bpy.props.BoolProperty(
        name="Custom Properties",
        description="Import user properties as custom properties",
        default=True,
    )
    use_custom_props_enum_as_string: bpy.props.BoolProperty(
        name="Import Enums As Strings",
        description="Store enumeration values as strings",
        default=True,
    )

    ignore_leaf_bones: bpy.props.BoolProperty(
        name="Ignore Leaf Bones",
        description="Ignore the last bone at the end of each chain (used to mark the length of the previous bone)",
        default=False,
    )
    force_connect_children: bpy.props.BoolProperty(
        name="Force Connect Children",
        description="Force connection of children bones to their parent, even if their computed head/tail "
        "positions do not match (can be useful with pure-joints-type armatures)",
        default=False,
    )
    automatic_bone_orientation: bpy.props.BoolProperty(
        name="Automatic Bone Orientation",
        description="Try to align the major bone axis with the bone children",
        default=False,
    )
    primary_bone_axis: bpy.props.EnumProperty(
        name="Primary Bone Axis",
        items=(
            ("X", "X Axis", ""),
            ("Y", "Y Axis", ""),
            ("Z", "Z Axis", ""),
            ("-X", "-X Axis", ""),
            ("-Y", "-Y Axis", ""),
            ("-Z", "-Z Axis", ""),
        ),
        default="Y",
    )
    secondary_bone_axis: bpy.props.EnumProperty(
        name="Secondary Bone Axis",
        items=(
            ("X", "X Axis", ""),
            ("Y", "Y Axis", ""),
            ("Z", "Z Axis", ""),
            ("-X", "-X Axis", ""),
            ("-Y", "-Y Axis", ""),
            ("-Z", "-Z Axis", ""),
        ),
        default="X",
    )

    use_prepost_rot: bpy.props.BoolProperty(
        name="Use Pre/Post Rotation",
        description="Use pre/post rotation from FBX transform (you may have to disable that in some cases)",
        default=True,
    )


class DDFBXIMPORT_OT_fbx_import(bpy.types.Operator):
    """Test importer that creates scripts nodes from .txt files"""

    bl_idname = "shader.script_import"
    bl_label = "Import a text file as a script node"

    """
    This Operator can import multiple .txt files, we need following directory and files
    properties that the file handler will use to set files path data
    """
    directory: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        return (
            context.region
            and context.region.type == "WINDOW"
            and context.area
            and context.area.ui_type == "ShaderNodeTree"
            and context.object
            and context.object.type == "MESH"
            and context.material
        )

    def execute(self, context):
        """The directory property need to be set."""
        if not self.directory:
            return {"CANCELLED"}
        x = 0.0
        y = 0.0
        for file in self.files:
            """
            Calls to the operator can set unfiltered file names,
            ensure the file extension is .txt
            """
            if file.name.endswith(".txt"):
                node_tree = context.material.node_tree
                text_node = node_tree.nodes.new(type="ShaderNodeScript")
                text_node.mode = "EXTERNAL"
                import os

                filepath = os.path.join(self.directory, file.name)
                text_node.filepath = filepath
                text_node.location = mathutils.Vector((x, y))
                x += 20.0
                y -= 20.0
        return {"FINISHED"}


"""---------------------------------------------------------
------------------------------------------------------------
    File Handler
------------------------------------------------------------
---------------------------------------------------------"""


class DDFBXIMPORT_FH_fbx_import(bpy.types.FileHandler):
    bl_idname = "SHADER_FH_script_import"
    bl_label = "File handler for shader script node import"
    bl_import_operator = "shader.script_import"
    bl_file_extensions = ".txt"

    @classmethod
    def poll_drop(cls, context):
        return (
            context.region
            and context.region.type == "WINDOW"
            and context.area
            and context.area.ui_type == "ShaderNodeTree"
        )


"""---------------------------------------------------------
------------------------------------------------------------
    REGISTER/UNREGISTER
------------------------------------------------------------
---------------------------------------------------------"""
CLASSES = (
    DDFBXIMPORT_OT_fbx_import,
    DDFBXIMPORT_FH_fbx_import,
)


def register():
    for cls in CLASSES:
        try:
            bpy.utils.register_class(cls)
        except:
            logger.debug(f"{cls.__name__} : already registred")

    ## Property Group の登録

    # デバッグ用
    # launch_debug_server()


def unregister():
    for cls in CLASSES:
        if hasattr(bpy.types, cls.__name__):
            bpy.utils.unregister_class(cls)
            logger.debug(f"{cls.__name__} unregistred")
