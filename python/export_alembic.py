# 3DE4.script.name:	Alembic...
# 3DE4.script.version:	v1.0
# 3DE4.script.gui:	Main Window::3DE4::Export Project
# 3DE4.script.comment:	Creates a Alembic export data.

import sys
import os
import re
from pprint import pprint

# Import alembic libs
from imath import *
from alembic.AbcCoreAbstract import *
from alembic.Abc import *
from alembic.AbcGeom import *


instpath = tde4.get3DEInstallPath()
if not "%s/sys_data/py_vl_sdv"%instpath in sys.path:
    sys.path.append("%s/sys_data/py_vl_sdv"%instpath)


# 3DEqualizer module import
from vl_sdv import *


# Convert Functions
def convertToAngles(r3d, yup):
    return tuple(rot3d(mat3d(r3d)).angles(VL_APPLY_ZXY))


def convertCameraToAngles(r3d, yup):
    return tuple(rot3d(mat3d(r3d)).angles(VL_APPLY_ZXY))


def convertZup(p3d, yup):
    return tuple([p3d[0],p3d[1],p3d[2]])


def angleMod360(d0, d):
    dd  = d - d0
    if dd > 3.141592654:
        d = angleMod360(d0,d - 3.141592654 * 2.0)
    else:
        if dd < -180.0:
            d = angleMod360(d0, d + 3.141592654 * 2.0)
    return d


def fill_array(itptraits, *input_list):
    array = itptraits.arrayType(len(input_list))
    for i in range(len(input_list)):
        array[i] = input_list[i]
    return array


def curve_sample(icurve, verts, num_verts, 
                                kcubic=CurveType.kCubic, 
                                knon_periodic=CurvePeriodicity.kPeriodic):

    curve = icurve.getSchema()
    curveSamp = OCurvesSchemaSample(verts, num_verts, kcubic, knon_periodic)

    knots = curveSamp.getKnots()
    assert len(knots) == 0

    newKnots = FloatArray(36)
    for ii in range(36):
        newKnots[ii] = ii
    curveSamp.setKnots(newKnots)

    knots = curveSamp.getKnots()
    for ii in range(4):
        assert knots[ii] == ii

    orders = curveSamp.getOrders()
    assert len(orders) == 0

    newOrder = UnsignedCharArray(3)
    for ii in range(3):
        newOrder[ii] = ii
    curveSamp.setOrders(newOrder)

    orders = curveSamp.getOrders()
    for ii in range(3):
        assert newOrder[ii] == ii

    curve.set(curveSamp)


def export_alembic():
	"""Main programm."""

	# Initialize parms
	cameras = tde4.getCameraList()
	point_grp = tde4.getPGroupList()

	if not all([cameras, point_grp]):
	    raise Exception("Error, not found cameras or point group.")

	camera_point_grp = None
	for grp in point_grp:
	    if tde4.getPGroupType(grp) == "CAMERA":
	        camera_point_grp = grp

	if not camera_point_grp:
	    raise Exception("Error, there is no camera point group.")

	points_list = tde4.getPointList(camera_point_grp)
	if points_list == []:
		raise Exception("Error, there is no point group.")
	   

	# Create file widget for save alembic
	req = tde4.createCustomRequester()
	tde4.addFileWidget(req, "file_browser", "Exportfile...", "*.abc")
	tde4.addTextFieldWidget(req, "startframe_field", "Startframe", "1")

	ret = tde4.postCustomRequester(req,"Export Alembic...", 540, 130, "Ok", "Cancel")
	file_path = tde4.getWidgetValue(req, "file_browser")

	if not file_path:
		raise Exception("Error, specify the path to save.")

	
	# Create alembic ouput path
	alembic_output_path = OArchive(file_path).getTop()

	count_camera = 1
	focal_length_mult = 10.0

	for camera in cameras:
	    camera_name = '%s%s' %(re.sub(r'[\# ]', '_', 
	                           tde4.getCameraName(camera)), count_camera)

	    # Get camera parms
	    camera_cur_frame = tde4.getCurrentFrame(camera)
	    camera_no_frames = tde4.getCameraNoFrames(camera)
	    camera_lens = tde4.getCameraLens(camera)
	    fback_width = tde4.getLensFBackWidth(camera_lens)
	    fback_height = tde4.getLensFBackHeight(camera_lens)
	    pixel_aspect = tde4.getLensPixelAspect(camera_lens)
	    focal_length = tde4.getCameraFocalLength(camera, 1) * focal_length_mult
	    image_width = tde4.getCameraImageWidth(camera)
	    image_height = tde4.getCameraImageHeight(camera)
	    window = -tde4.getLensLensCenterX(camera_lens) * focal_length_mult / fback_width, \
	             -tde4.getLensLensCenterY(camera_lens) * focal_length_mult / fback_height
	    fps = tde4.getCameraFPS(camera)

	    # Current camera number
	    count_camera += 1

	    translate = [] 
	    rotate = []


	    # Find the position and rotation of the camera
	    for f in range(camera_cur_frame, camera_no_frames + 1):
	        pos3d = tde4.getPGroupPosition3D(camera_point_grp, camera, f)
	        pos3d = convertZup(pos3d, 0)
	        rot3d = tde4.getPGroupRotation3D(camera_point_grp, camera, f)
	        rot = convertCameraToAngles(rot3d, 0)
	        rot = [rot[0] * (180 / math.pi), rot[1] * (180 / math.pi), rot[2] * (180 / math.pi)]

	        #rot = [angleMod360(rot[0], rot[0]), angleMod360(rot[1], rot[1]), angleMod360(rot[2], rot[2])]

	        translate.append(pos3d)
	        rotate.append(rot)

	    #pprint(rotate)

	    # Sampling the camera parameters according to the frame
	    timesamp = TimeSampling(1.0 / fps, camera_cur_frame / fps)
	    tsidx = alembic_output_path.getArchive().addTimeSampling(timesamp)

	    # Create parent Xform 
	    xform = OXform(alembic_output_path, camera_name, tsidx)
	    xsamp = XformSample()

	    for i in range(camera_no_frames):
	        samp = CameraSample()
	        # Set translate and rotate camera
	        xsamp.setTranslation(V3d(translate[i]))
	        rot = rotate[i]
	        xsamp.setZRotation(rot[2])
	        xsamp.setYRotation(rot[1])
	        xsamp.setXRotation(rot[0])

	        xform.getSchema().set(xsamp)

	    camera = OCamera(xform, camera_name)

	    # Output resolution
	    user_props = camera.getSchema().getUserProperties()
	    resx = OFloatProperty(user_props, "resx")
	    resy = OFloatProperty(user_props, "resy")

	    resx.setValue(image_width)
	    resy.setValue(image_height)

	    samp = CameraSample()
	    
	    # Camera parms
	    samp.setLensSqueezeRatio(pixel_aspect)
	    samp.setHorizontalAperture(fback_width)
	    samp.setFocalLength(focal_length)
	    samp.setHorizontalFilmOffset(window[0])
	    samp.setVerticalFilmOffset(window[1])

	    camera.getSchema().set(samp)

	# Create auxiliary locators
	group_points_name = "cameraPGroup_%s_1" % tde4.getPGroupName(camera_point_grp)
	points_list = tde4.getPointList(camera_point_grp)

	# Dimensions of the locator
	verts = fill_array(V3fTPTraits,

	    # first primitive
	    V3f (-0.5, 0, 0.0),
	    V3f (-0.2, 0.0, 0.0),
	    V3f (0.2, 0, 0.0),
	    V3f (0.5, 0, 0.0),

	    # second primitive
	    V3f (0.0, -0.5, 0.0),
	    V3f (0.0, -0.2, 0.0),
	    V3f (0.0, 0.2, 0.0),
	    V3f (0.0, 0.5, 0.0),

	    # third primitive
	    V3f (0.0, 0.0, -0.5),
	    V3f (0.0, 0.0, -0.2),
	    V3f (0.0, 0.0, 0.2),
	    V3f (0.0, 0.0, 0.5)

	)

	num_verts = fill_array(Int32TPTraits, 4, 4, 4)

	xform = OXform(alembic_output_path, group_points_name)
	
	for index, point in enumerate(points_list):
	    if tde4.isPointCalculated3D(camera_point_grp, point):
	        name = "p%s" % tde4.getPointName(camera_point_grp, point)
	        pos3d = tde4.getPointCalcPosition3D(camera_point_grp, point)
	        pos3d = convertZup(pos3d, 0)

	        xform_locator = OXform(xform, name)
	        pos = V3d(pos3d)
	        xsamp = XformSample()
	        xsamp.setTranslation(pos)
	        xform_locator.getSchema().set(xsamp)

	        curve = OCurves(xform_locator, name)
	        curve_sample(curve, verts, num_verts)

	tde4.postQuestionRequester("Export Alembic...","Project successfully exported.", "Ok")
	tde4.deleteCustomRequester(req)

export_alembic()