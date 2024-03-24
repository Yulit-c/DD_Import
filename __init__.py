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
from bpy_extras.io_utils import orientation_helper
from addon_utils import paths, check
from bpy.path import module_names

from pathlib import Path
from typing import Any

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
    Variables
------------------------------------------------------------
---------------------------------------------------------"""
presets_directory: Path = Path(bpy.utils.resource_path("USER")).joinpath("scripts", "presets", "DDFBXImport")


"""---------------------------------------------------------
------------------------------------------------------------
    Functions
------------------------------------------------------------
---------------------------------------------------------"""


def get_enabled_addon_list():
    enabled_addon_list = []
    for path in paths():
        for mod_name, mod_path in module_names(path):
            is_enabled, is_loaded = check(mod_name)
            if is_enabled:
                enabled_addon_list.append(mod_name)
    return enabled_addon_list


def get_preset_directory() -> Path:
    importer = get_ddfbx_addon_preferences().importer
    match int(importer):
        case 0:
            source_directory = presets_directory.joinpath("BuiltIn")

        case 1:
            source_directory = presets_directory.joinpath("BetterFBX")
    return source_directory


"""---------------------------------------------------------
------------------------------------------------------------
    Addon Preference
------------------------------------------------------------
---------------------------------------------------------"""


class DDFBXIMPORT_PREF_addon_preference(bpy.types.AddonPreferences):
    bl_idname = __package__

    def get_item_list(scene, context) -> list[tuple[str]]:
        items = [("0", "Built-In", "")]
        if "better_fbx" in get_enabled_addon_list():
            items.append(("1", "Better FBX", ""))
        return items

    importer: bpy.props.EnumProperty(
        name="Importer",
        description="Description",
        items=get_item_list,
        default=0,
    )

    show_popup: bpy.props.BoolProperty(
        name="Show Popup Import Option",
        description="",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        split_factor = 0.5

        header, panel = layout.panel("DDFBX_Pref_Importer", default_closed=False)
        header.label(text="Importer")
        if panel:
            row = panel.row(align=True)
            row.separator(factor=5.0)
            sp = row.split(align=True, factor=split_factor)
            sp.label(text="Importer")
            sp.prop(self, "importer", text="")

        header, panel = layout.panel("DDFBX_Pref_Behavior", default_closed=False)
        header.label(text="Behavior")
        if panel:
            row = panel.row(align=True)
            row.separator(factor=5.0)
            sp = row.split(align=True, factor=split_factor)
            sp.label(text="Show Popup")
            sp.prop(self, "show_popup", text="")


def get_ddfbx_addon_preferences() -> DDFBXIMPORT_PREF_addon_preference:
    """
    アドオンが定義したプリファレンスの変数を取得して使用できるようにする｡
    自身のパッケージ名からプリファレンスを取得する｡


    Returns
    -------
    AddonPreferences
        取得したプリファレンスのインスタンス
    """

    splitted_package_name = __package__.split(".")[0]
    addon_preferences = bpy.context.preferences.addons[splitted_package_name].preferences

    return addon_preferences


"""---------------------------------------------------------
------------------------------------------------------------
    Property Group
------------------------------------------------------------
---------------------------------------------------------"""


class PropertyGroupBase:
    def get_parameters_as_dict(self):
        dic_op_parameters = {}
        # 選択されているインポーターに応じたプロパティグループを取得する
        match int(get_ddfbx_addon_preferences().importer):
            case 0:
                importer_prop = get_wm_built_in_property_groups()
            case 1:
                importer_prop = get_wm_better_fbx_property_groups()
        # 取得したプロパティグループの全てのフィールドの値を辞書として取得する
        [dic_op_parameters.setdefault(k, getattr(importer_prop, k)) for k in [*importer_prop.__annotations__]]
        return dic_op_parameters

    def set_parameters(
        self, target_object: bpy.types.Operator | bpy.types.PropertyGroup, parameters: dict[Any]
    ):
        # 取得したパラメーターをOperatorまたはPropertyGroupの値にセットする｡
        for k, v in parameters.items():
            setattr(target_object, k, v)


@orientation_helper(axis_forward="-Z", axis_up="Y")
class BuiltInPropertyGroups(PropertyGroupBase):
    # ----------------------------------------------------------
    #    for Importer
    # ----------------------------------------------------------
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


class BetterFBXPropertyGroups(PropertyGroupBase):
    # ----------------------------------------------------------
    #    for Importer
    # ----------------------------------------------------------
    use_auto_bone_orientation: bpy.props.BoolProperty(
        name="Automatic Bone Orientation",
        description="Automatically sort bones orientations, if you want to preserve the original armature, please disable the option",
        default=True,
    )

    my_calculate_roll: bpy.props.EnumProperty(
        name="Calculate Roll",
        description="Automatically fix alignment of imported bones’ axes when 'Automatic Bone Orientation' is enabled",
        items=(
            ("POS_X", "POS_X", "POS_X"),
            ("POS_Z", "POS_Z", "POS_Z"),
            ("GLOBAL_POS_X", "GLOBAL_POS_X", "GLOBAL_POS_X"),
            ("GLOBAL_POS_Y", "GLOBAL_POS_Y", "GLOBAL_POS_Y"),
            ("GLOBAL_POS_Z", "GLOBAL_POS_Z", "GLOBAL_POS_Z"),
            ("NEG_X", "NEG_X", "NEG_X"),
            ("NEG_Z", "NEG_Z", "NEG_Z"),
            ("GLOBAL_NEG_X", "GLOBAL_NEG_X", "GLOBAL_NEG_X"),
            ("GLOBAL_NEG_Y", "GLOBAL_NEG_Y", "GLOBAL_NEG_Y"),
            ("GLOBAL_NEG_Z", "GLOBAL_NEG_Z", "GLOBAL_NEG_Z"),
            ("ACTIVE", "ACTIVE", "ACTIVE"),
            ("VIEW", "VIEW", "VIEW"),
            ("CURSOR", "CURSOR", "CURSOR"),
            ("None", "None", "Does not fix alignment of imported bones’ axes"),
        ),
        default="None",
    )

    my_bone_length: bpy.props.FloatProperty(
        name="Bone Length",
        description="Bone length when 'Automatic Bone Orientation' is disabled",
        default=10.0,
        min=0.0001,
        max=10000.0,
    )

    my_leaf_bone: bpy.props.EnumProperty(
        name="Leaf Bone",
        description="The length of leaf bone",
        items=(("Long", "Long", "1/1 length of its parent"), ("Short", "Short", "1/10 length of its parent")),
        default="Long",
    )

    use_fix_bone_poses: bpy.props.BoolProperty(
        name="Fix Bone Poses",
        description="Try fixing bone poses with default poses whenever bind poses are not equal to default poses",
        default=False,
    )

    use_fix_attributes: bpy.props.BoolProperty(
        name="Fix Attributes For Unity & C4D",
        description="Try fixing null attributes for Unity's FBX exporter & C4D's FBX exporter, but it may bring extra fake bones",
        default=True,
    )

    use_only_deform_bones: bpy.props.BoolProperty(
        name="Only Deform Bones",
        description="Import only deform bones",
        default=False,
    )

    primary_bone_axis: bpy.props.EnumProperty(
        name="Primary Bone Axis",
        description="User defined primary bone axis, only take effect when the 'Automatic Bone Orientation' option is disabled",
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
        description="User defined primary bone axis, only take effect when the 'Automatic Bone Orientation' option is disabled",
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

    use_vertex_animation: bpy.props.BoolProperty(
        name="Vertex Animation",
        description="Import vertex animation",
        default=True,
    )

    use_animation: bpy.props.BoolProperty(
        name="Animation",
        description="Import animation",
        default=True,
    )

    use_attach_to_selected_armature: bpy.props.BoolProperty(
        name="Attach To Selected Armature",
        description="Do not create a new armature, but attach the imported animation to an existing armature, two armatures must have exactly the same hierarchy",
        default=False,
    )

    my_animation_offset: bpy.props.IntProperty(
        name="Animation Offset",
        description="Add an offset to all keyframes",
        default=0,
        min=-1000000,
        max=1000000,
    )

    use_animation_prefix: bpy.props.BoolProperty(
        name="Animation Prefix",
        description="Add object name as animation prefix",
        default=False,
    )

    use_pivot: bpy.props.BoolProperty(
        name="Pivot To Origin",
        description="Apply rotation pivot to origin",
        default=False,
    )

    use_triangulate: bpy.props.BoolProperty(
        name="Triangulate",
        description="Triangulate meshes",
        default=False,
    )

    my_import_normal: bpy.props.EnumProperty(
        name="Normal",
        description="How to get normals",
        items=(
            ("Calculate", "Calculate", "Let Blender generate normals"),
            ("Import", "Import", "Use imported normals"),
        ),
        default="Import",
    )

    use_auto_smooth: bpy.props.BoolProperty(
        name="Auto Smooth",
        description="Auto smooth (based on smooth/sharp faces/edges and angle between faces)",
        default=True,
    )

    my_angle: bpy.props.FloatProperty(
        name="Angle",
        description="Maximum angle between face normals that will be considered as smooth",
        default=60.0,
        min=0.0,
        max=180.0,
    )

    my_shade_mode: bpy.props.EnumProperty(
        name="Shading",
        description="How to render and display faces",
        items=(
            ("Smooth", "Smooth", "Render and display faces smooth, using interpolated vertex normals"),
            ("Flat", "Flat", "Render and display faces uniform, using face normals"),
        ),
        default="Smooth",
    )

    my_scale: bpy.props.FloatProperty(
        name="Scale", description="Scale all data", default=1.0, min=0.0001, max=10000.0
    )

    use_optimize_for_blender: bpy.props.BoolProperty(
        name="Optimize For Blender",
        description="Make Blender friendly translation, rotation and scaling",
        default=False,
    )

    use_reset_mesh_origin: bpy.props.BoolProperty(
        name="Reset Mesh Origin",
        description="Reset mesh origin to zero when 'Optimize For Blender' is enabled",
        default=True,
    )

    use_reset_mesh_rotation: bpy.props.BoolProperty(
        name="Reset Mesh Rotation",
        description="Reset mesh rotation to zero when 'Optimize For Blender' is enabled",
        default=True,
    )

    use_edge_crease: bpy.props.BoolProperty(
        name="Edge Crease",
        description="Import edge crease",
        default=True,
    )

    my_edge_crease_scale: bpy.props.FloatProperty(
        name="Edge Crease Scale",
        description="Scale of the edge crease value",
        default=1.0,
        min=0.0001,
        max=10000.0,
    )

    my_edge_smoothing: bpy.props.EnumProperty(
        name="Smoothing Groups",
        description="How to generate smoothing groups",
        items=(
            ("None", "None", "Does not generate smoothing groups"),
            ("Import", "Import From File", "Import smoothing groups from file"),
            ("FBXSDK", "Generate By FBX SDK", "Generate smoothing groups from normals by FBX SDK"),
            ("Blender", "Generate By Blender", "Generate smoothing groups from normals by Blender"),
        ),
        default="FBXSDK",
    )

    use_detect_deform_bone: bpy.props.BoolProperty(
        name="Detect Deform Bone",
        description="Detect and setup deform bones automatically, if you are importing a pure armature which is not skinned by any meshes, please disable the option, otherwise, all bones will be wrongly setup as non-deform bones",
        default=True,
    )

    use_import_materials: bpy.props.BoolProperty(
        name="Import Materials",
        description="Import materials for meshes, if you don't want to import any materials, you can turn off this option",
        default=True,
    )

    use_rename_by_filename: bpy.props.BoolProperty(
        name="Rename By Filename",
        description="If you want to import a lot of 3d models or armatures in batch, and there is only one mesh or one armature per file, you may turn on this option to rename the imported meshes or armatures by their filenames",
        default=False,
    )

    use_fix_mesh_scaling: bpy.props.BoolProperty(
        name="Fix Mesh Scaling",
        description="Sometimes the evaluated scaling is wrong, we can try fixing the scaling with the stored local scaling",
        default=False,
    )

    my_rotation_mode: bpy.props.EnumProperty(
        name="Rotation Mode",
        description="Rotation mode of all objects",
        items=(
            ("QUATERNION", "Quaternion (WXYZ)", "Quaternion (WXYZ), No Gimbal Lock"),
            ("XYZ", "XYZ Euler", "XYZ Rotation Order - prone to Gimbal Lock"),
            ("XZY", "XZY Euler", "XZY Rotation Order - prone to Gimbal Lock"),
            ("YXZ", "YXZ Euler", "YXZ Rotation Order - prone to Gimbal Lock"),
            ("YZX", "YZX Euler", "YZX Rotation Order - prone to Gimbal Lock"),
            ("ZXY", "ZXY Euler", "ZXY Rotation Order - prone to Gimbal Lock"),
            ("ZYX", "ZYX Euler", "ZYX Rotation Order - prone to Gimbal Lock"),
            (
                "AXIS_ANGLE",
                "Axis Angle",
                "Axis Angle (W+XYZ), defines a rotation around some axis defined by 3D-Vector",
            ),
        ),
        default="QUATERNION",
    )

    my_fbx_unit: bpy.props.EnumProperty(
        name="FBX Unit",
        description="FBX Unit",
        items=(
            ("mm", "mm", "mm"),
            ("dm", "dm", "dm"),
            ("cm", "cm", "cm"),
            ("m", "m", "m"),
            ("km", "km", "km"),
            ("Inch", "Inch", "Inch"),
            ("Foot", "Foot", "Foot"),
            ("Mile", "Mile", "Mile"),
            ("Yard", "Yard", "Yard"),
        ),
        default="cm",
    )


class DDFBXIMPORT_WM_built_in_import_options(bpy.types.PropertyGroup, BuiltInPropertyGroups):
    pass


class DDFBXIMPORT_WM_better_fbx_import_options(bpy.types.PropertyGroup, BetterFBXPropertyGroups):
    pass


class DDFBXIMPORT_WM_import_options_root(bpy.types.PropertyGroup):
    built_in: bpy.props.PointerProperty(
        name="Built-In Importer",
        description="",
        type=DDFBXIMPORT_WM_built_in_import_options,
    )

    better_fbx: bpy.props.PointerProperty(
        name="Better FBX",
        description="",
        type=DDFBXIMPORT_WM_better_fbx_import_options,
    )


def get_wm_built_in_property_groups() -> DDFBXIMPORT_WM_built_in_import_options:
    root_property: DDFBXIMPORT_WM_import_options_root = bpy.context.window_manager.ddfbx_importer
    importer_prop = root_property.built_in
    return importer_prop


def get_wm_better_fbx_property_groups() -> DDFBXIMPORT_WM_better_fbx_import_options:
    root_property: DDFBXIMPORT_WM_import_options_root = bpy.context.window_manager.ddfbx_importer
    importer_prop = root_property.better_fbx
    return importer_prop


"""---------------------------------------------------------
------------------------------------------------------------
    Operator
------------------------------------------------------------
---------------------------------------------------------"""


class DDFBXIMPORT_ImportOperatorBase(bpy.types.Operator):

    # File Handlerから受け取ったファイル名の文字列からファイルパスを生成する
    def gen_source_file_list(self, source_file_names: [str]) -> list[str]:
        file_list = [i.strip() for i in source_file_names[1:-1].split(",")]
        return file_list

    # インポート対象のファイルのパスを生成する
    def gen_source_file_path(self, source_dir: str, source_file_name: str) -> Path:
        file_name = source_file_name[1:-1]
        file_path = Path(source_dir).joinpath(file_name)
        logger.debug(file_path)
        return file_path


class DDFBXIMPORT_OT_built_in_import(DDFBXIMPORT_ImportOperatorBase, BuiltInPropertyGroups):
    bl_idname = "ddfbx.built_in_import"
    bl_label = "Built-In Import"
    bl_description = ""
    bl_options = {"UNDO", "PRESET"}

    # ----------------------------------------------------------
    #    for File Handler
    # ----------------------------------------------------------
    directory: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})
    files: bpy.props.StringProperty(options={"SKIP_SAVE"})

    # ----------------------------------------------------------
    #    for UI
    # ----------------------------------------------------------
    expand_include: bpy.props.BoolProperty(
        name="Expand Include",
        description="",
        default=True,
    )
    expand_transform: bpy.props.BoolProperty(
        name="Expand Transform",
        description="",
        default=True,
    )
    expand_orientation: bpy.props.BoolProperty(
        name="Expand Orienation",
        description="",
        default=True,
    )
    expand_animation: bpy.props.BoolProperty(
        name="Expand Animation",
        description="",
        default=True,
    )
    expand_armature: bpy.props.BoolProperty(
        name="Expand Armature",
        description="",
        default=True,
    )

    # ----------------------------------------------------------
    #    Operator Method
    # ----------------------------------------------------------
    def invoke(self, context, event):
        logger.debug("Invoke")
        # オペレーターに対応するプロパティグループの値を取得する
        parameters_dict = self.get_parameters_as_dict()
        # 取得した値をオペレーターのプロパティに値を瀬とする
        self.set_parameters(self, parameters_dict)
        return context.window_manager.invoke_props_dialog(self, width=360)

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        row = box.row(align=True)
        if not self.expand_include:
            row.prop(self, "expand_include", icon="TRIA_RIGHT", icon_only=True, emboss=False)
            row.separator(factor=2.0)
            row.label(text="Include")
        else:
            row.prop(self, "expand_include", icon="TRIA_DOWN", icon_only=True, emboss=False)
            row.separator(factor=2.0)
            row.label(text="Include")
            row = box.row(align=True)
            row.separator(factor=3.0)
            col = row.column()

            col.use_property_split = True
            col.use_property_decorate = False

            col.prop(self, "use_custom_normals")
            col.prop(self, "use_subsurf")
            col.prop(self, "use_custom_props")
            sub = col.row()
            sub.enabled = self.use_custom_props
            sub.prop(self, "use_custom_props_enum_as_string")
            col.prop(self, "use_image_search")
            col.prop(self, "colors_type")

        box = layout.box()
        row = box.row(align=True)
        if not self.expand_transform:
            row.prop(self, "expand_transform", icon="TRIA_RIGHT", icon_only=True, emboss=False)
            row.separator(factor=2.0)
            row.label(text="Transform")
        else:
            row.prop(self, "expand_transform", icon="TRIA_DOWN", icon_only=True, emboss=False)
            row.separator(factor=2.0)
            row.label(text="Transform")
            row = box.row(align=True)
            row.separator(factor=3.0)
            col = row.column()

            col.use_property_split = True
            col.use_property_decorate = False  # No Animation

            col.prop(self, "global_scale")
            col.prop(self, "decal_offset")
            row = col.row()
            row.prop(self, "bake_space_transform")
            row.label(text="", icon="ERROR")
            col.prop(self, "use_prepost_rot")

        box = layout.box()
        row = box.row(align=True)
        if not self.expand_orientation:
            row.prop(self, "expand_orientation", icon="TRIA_RIGHT", icon_only=True, emboss=False)
            row.prop(self, "use_manual_orientation", text="")
            row.label(text="Manual Orientation")
        else:
            row.prop(self, "expand_orientation", icon="TRIA_DOWN", icon_only=True, emboss=False)
            row.prop(self, "use_manual_orientation", text="")
            row.label(text="Manual Orientation")
            row = box.row(align=True)
            row.separator(factor=3.0)
            col = row.column()

            col.use_property_split = True
            col.use_property_decorate = False  # No Animation.

            sub = col.column()
            sub.enabled = self.use_manual_orientation
            sub.prop(self, "axis_forward")
            sub.prop(self, "axis_up")

        box = layout.box()
        row = box.row(align=True)
        if not self.expand_animation:
            row.prop(self, "expand_animation", icon="TRIA_RIGHT", icon_only=True, emboss=False)
            row.prop(self, "use_anim", text="")
            row.label(text="Animation")
        else:
            row.prop(self, "expand_animation", icon="TRIA_DOWN", icon_only=True, emboss=False)
            row.prop(self, "use_anim", text="")
            row.label(text="Animation")
            row = box.row(align=True)
            row.separator(factor=3.0)
            col = row.column()

            col.use_property_split = True
            col.use_property_decorate = False

            sub = col.column()
            sub.enabled = self.use_anim
            sub.prop(self, "anim_offset")

        box = layout.box()
        row = box.row(align=True)
        if not self.expand_armature:
            row.prop(self, "expand_armature", icon="TRIA_RIGHT", icon_only=True, emboss=False)
            row.separator(2.0)
            row.label(text="Armature")
        else:
            row.label(text="", icon="TRIA_DOWN")
            row.prop(self, "expand_armature", icon="TRIA_DOWN", icon_only=True, emboss=False)
            row.label(text="Armature")
            row = box.row(align=True)
            row.separator(factor=3.0)
            col = row.column()

            col.use_property_split = True
            col.use_property_decorate = False

            col.prop(self, "ignore_leaf_bones")
            col.prop(self, "force_connect_children")
            col.prop(self, "automatic_bone_orientation")
            sub = col.column()
            sub.enabled = not self.automatic_bone_orientation
            sub.prop(self, "primary_bone_axis")
            sub.prop(self, "secondary_bone_axis")

    def execute(self, context):
        ignore_props = (
            "filter_glob",
            "directory",
            "ui_tab",
            "filepath",
            "files",
            "expand_include",
            "expand_transform",
            "expand_orientation",
            "expand_animation",
            "expand_armature",
        )
        # オペレーターのプロパティの値をWindowManagerのプロパティグループに保存する
        operator_parameters = self.as_keywords(ignore=ignore_props)
        built_in_property_group = get_wm_built_in_property_groups()
        for k, v in operator_parameters.items():
            setattr(built_in_property_group, k, v)
        # File Handlerから受け取ったファイル名の文字列からファイルパスを生成する
        file_list = self.gen_source_file_list(self.files)
        for i in file_list:
            file_path = self.gen_source_file_path(self.directory, i)

            # オペレーターのプロパティグループを引数としてインポートオペレーターを呼び出す
            keywords = self.as_keywords(ignore=ignore_props)
            bpy.ops.import_scene.fbx(filepath=str(file_path), **keywords)
            logger.debug(f'Load Complete\n{"":#<70}')

        return {"FINISHED"}


class DDFBXIMPORT_OT_better_fbx_import(DDFBXIMPORT_ImportOperatorBase, BetterFBXPropertyGroups):
    bl_idname = "ddfbx.better_fbx_import"
    bl_label = "Better FBX Import"
    bl_description = ""
    bl_options = {"UNDO", "PRESET"}

    # ----------------------------------------------------------
    #    for File Handler
    # ----------------------------------------------------------
    directory: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})
    files: bpy.props.StringProperty(options={"SKIP_SAVE"})

    # ----------------------------------------------------------
    #    Operator Method
    # ----------------------------------------------------------
    def invoke(self, context, event):
        logger.debug("Invoke")
        # オペレーターに対応するプロパティグループの値を取得する
        parameters_dict = self.get_parameters_as_dict()
        # 取得した値をオペレーターのプロパティに値を瀬とする
        self.set_parameters(self, parameters_dict)
        return context.window_manager.invoke_props_dialog(self, width=360)

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Basic Options:")
        box.prop(self, "my_rotation_mode")
        box.prop(self, "my_import_normal")
        box.prop(self, "use_auto_smooth")
        box.prop(self, "my_angle")
        box.prop(self, "my_shade_mode")
        box.prop(self, "my_fbx_unit")
        box.prop(self, "my_scale")

        box = layout.box()
        box.label(text="Blender Options:")
        box.prop(self, "use_optimize_for_blender")
        row = box.row()
        row.prop(self, "use_reset_mesh_origin")
        row.enabled = self.use_optimize_for_blender
        row = box.row()
        row.prop(self, "use_reset_mesh_rotation")
        row.enabled = self.use_optimize_for_blender

        box = layout.box()
        box.label(text="Bone Options:")
        box.prop(self, "use_auto_bone_orientation")
        row = box.row()
        row.prop(self, "primary_bone_axis")
        row.enabled = not self.use_auto_bone_orientation
        row = box.row()
        row.prop(self, "secondary_bone_axis")
        row.enabled = not self.use_auto_bone_orientation
        row = box.row()
        row.prop(self, "my_calculate_roll")
        row.enabled = self.use_auto_bone_orientation
        box.prop(self, "my_bone_length")
        box.prop(self, "my_leaf_bone")
        box.prop(self, "use_detect_deform_bone")
        box.prop(self, "use_fix_bone_poses")
        box.prop(self, "use_fix_attributes")
        box.prop(self, "use_only_deform_bones")

        box = layout.box()
        box.label(text="Animation Options:")
        box.prop(self, "use_animation")
        box.prop(self, "use_attach_to_selected_armature")
        box.prop(self, "my_animation_offset")
        box.prop(self, "use_animation_prefix")

        box = layout.box()
        box.label(text="Vertex Animation Options:")
        box.prop(self, "use_vertex_animation")

        box = layout.box()
        box.label(text="Material Options:")
        box.prop(self, "use_import_materials")

        box = layout.box()
        box.label(text="Mesh Options:")
        box.prop(self, "use_pivot")
        box.prop(self, "use_triangulate")
        box.prop(self, "use_rename_by_filename")
        box.prop(self, "use_fix_mesh_scaling")

        box = layout.box()
        box.label(text="Edge Options:")
        box.prop(self, "my_edge_smoothing")
        box.prop(self, "use_edge_crease")
        box.prop(self, "my_edge_crease_scale")

    def execute(self, context):
        ignore_props = (
            "directory",
            "files",
        )
        # オペレーターのプロパティの値をWindowManagerのプロパティグループに保存する
        operator_parameters = self.as_keywords(ignore=ignore_props)
        better_fbx_property_group = get_wm_better_fbx_property_groups()
        for k, v in operator_parameters.items():
            setattr(better_fbx_property_group, k, v)
        # File Handlerから受け取ったファイル名の文字列からファイルパスを生成する
        # file_list = [i.strip() for i in self.files[1:-1].split(",")]
        file_list = self.gen_source_file_list(self.files)
        for i in file_list:
            # file_name = i[1:-1]
            # file_path = Path(self.directory).joinpath(file_name)
            # logger.debug(file_path)
            file_path = self.gen_source_file_path(self.directory, i)

            # オペレーターのプロパティグループを引数としてインポートオペレーターを呼び出す
            keywords = self.as_keywords(ignore=ignore_props)
            bpy.ops.better_import.fbx(filepath=str(file_path), **keywords)
            logger.debug(f'Load Complete\n{"":#<70}')

        return {"FINISHED"}


class DDFBXIMPORT_OT_fbx_import(bpy.types.Operator):
    """Test importer that creates scripts nodes from .txt files"""

    bl_idname = "ddfbx.fbx_import"
    bl_label = "D&D Import FBX"

    """
    This Operator can import multiple .txt files, we need following directory and files
    properties that the file handler will use to set files path data
    """
    directory: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == "VIEW_3D"

    def execute(self, context):
        import os

        os.system("cls")
        """The directory property need to be set."""
        if not self.directory:
            return {"CANCELLED"}

        # Better FBXがインストールされていない場合はEnumアイテムを0に設定
        if not "better_fbx" in get_enabled_addon_list():
            get_ddfbx_addon_preferences().importer = "0"

        # Show Popupの値に応じてExecution Contextを定義する
        addon_pref = get_ddfbx_addon_preferences()
        selected_importer = addon_pref.importer
        if addon_pref.show_popup:
            exec_context = "INVOKE_DEFAULT"
        else:
            exec_context = "EXEC_DEFAULT"

        # Preferenceで選択されたインポーターに応じたオペレーターを実行する｡
        match int(selected_importer):
            case 0:  # Built-In
                logger.debug("Mode 0")
                bpy.ops.ddfbx.built_in_import(
                    exec_context, directory=self.directory, files=str(self.files.keys())
                )
            case 1:  # Better FBX
                logger.debug("Mode 1")
                bpy.ops.ddfbx.better_fbx_import(
                    exec_context, directory=self.directory, files=str(self.files.keys())
                )

        return {"FINISHED"}


"""---------------------------------------------------------
------------------------------------------------------------
    File Handler
------------------------------------------------------------
---------------------------------------------------------"""


class DDFBXIMPORT_FH_fbx_import(bpy.types.FileHandler):
    bl_idname = "DDFBXIMPORT_FH_custom_fbx_import"
    bl_label = "File Handler for Custom FBX Import"
    bl_import_operator = "ddfbx.fbx_import"
    bl_file_extensions = ".fbx"

    @classmethod
    def poll_drop(cls, context):
        return context.area and context.area.type == "VIEW_3D"


"""---------------------------------------------------------
------------------------------------------------------------
    REGISTER/UNREGISTER
------------------------------------------------------------
---------------------------------------------------------"""
CLASSES = (
    DDFBXIMPORT_PREF_addon_preference,
    DDFBXIMPORT_WM_built_in_import_options,
    DDFBXIMPORT_WM_better_fbx_import_options,
    DDFBXIMPORT_WM_import_options_root,
    DDFBXIMPORT_OT_built_in_import,
    DDFBXIMPORT_OT_better_fbx_import,
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
    bpy.types.WindowManager.ddfbx_importer = bpy.props.PointerProperty(
        type=DDFBXIMPORT_WM_import_options_root
    )

    # デバッグ用
    # launch_debug_server()


def unregister():
    # Property Group の削除
    del bpy.types.WindowManager.ddfbx_importer
    for cls in CLASSES:
        if hasattr(bpy.types, cls.__name__):
            bpy.utils.unregister_class(cls)
            logger.debug(f"{cls.__name__} unregistred")
