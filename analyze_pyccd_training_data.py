import os
import sys
import numpy as np
from osgeo import gdal
import glob

from geo_utils import ChipExtents
from subset_trends import SubsetTrends
from json_utils import JSONReader

WKT = '''PROJCS["Albers",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378140,298.2569999999957,AUTHORITY["EPSG",
"7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]],
PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["standard_parallel_1",29.5],PARAMETER["standard_parallel_2",45.5],
PARAMETER["latitude_of_center",23],PARAMETER["longitude_of_center",-96],PARAMETER["false_easting",0],
PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]]]'''

class CheckTrainingData:

    def __init__(self, h=5, v=2, in_trends=r"Z:\ancillary\training\trends.tif",
                 out_dir=r"C:\Users\dzelenak\Workspace\LCMAP_Eval\ARD_h05v02\class\ancillary",
                 json_dir=r'Z:\sites\washington\pyccd-results\H05V02\2017.06.20\json'):

        self.in_trends = in_trends
        self.out_dir = out_dir
        self.out_trends = self.out_dir + os.sep + "trends_chips"

        if not os.path.exists(self.out_trends):

            os.makedirs(self.out_trends)

        self.H = h
        self.V = v

        self.JSON_DIR = json_dir

        self.chip_info = ChipExtents(self.H, self.V)

        self.chip_extents = self.chip_info.CHIP_EXTENTS

        # self.json_tools = JSONReader(self.JSON_DIR)

    def analyze_chips(self):

        counter = 1.0

        json_reader = JSONReader(self.JSON_DIR)

        for chip in self.chip_extents:

            current = counter / len(self.chip_extents) * 100.0

            print("\nAnalyzing Chip {} of 2500\n".format(chip))

            # subset the CONUS trends to the current chip extent

            trends_chip = self.out_trends + os.sep + "trends_{}.tif".format(chip)

            if os.path.exists(trends_chip):

                os.remove(trends_chip)

            trends = SubsetTrends(self.in_trends, trends_chip, self.chip_extents[chip])

            # generate the trends mask for the the current chip
            # anywhere that trends > 0 is True
            trends_mask = trends.test_data(trends.data)

            if np.any(trends_mask):

                print("\n\tFound Trends data for chip {}\n".format(chip))
                # for the current chip generate the pixel UL coordinates if trends data is present
                # self.pixel_coords = self.chip_info.get_pixel_coords(self.chip_extents[chip])

                # trends.data is the original trends clipped to the chip extent
                out_mask = np.zeros_like(trends.data, dtype=np.uint8).flatten()

                out_mask[ trends.data.flatten() > 0 ] = 1

                json_results = json_reader.get_jsonchip(h=self.H, v=self.V,
                                                    chip_coord=self.chip_extents[chip]).flatten()[trends_mask.flatten()]

                sliced = out_mask[trends_mask.flatten()]

                for index, result in enumerate(json_results):

                    if len(result['change_models']) > 0:

                        # TODO implement logging

                        sliced[index] = json_reader.check_time_segment_with_training(results=result)

                    else:

                        # Case for when PyCCD coverage = 0, still count as good Trends Data
                        sliced[index] = 1

                out_mask[trends_mask.flatten()] = sliced

                out_mask = out_mask.reshape((100,100))

                print("\nGenerating new raster from time_segment & trends mask\n")

                if np.any(out_mask):

                    self.array_to_raster(chip=chip, mask=out_mask, rsc=trends_chip)

            # show the percent complete
            sys.stdout.write("\r%s%% Done " % str(current)[:5])

            # needed to display the current percent complete
            sys.stdout.flush()

            counter += 1.0

        sys.stdout.flush()

        return None

    def array_to_raster(self, chip, mask, rsc):

        driver = gdal.GetDriverByName("GTiff")

        src0 = gdal.Open(rsc, gdal.GA_ReadOnly)

        out_str = self.out_dir + "{a}chips{a}mask_{b}.tif".format(a=os.sep, b=chip)

        if not os.path.exists(os.path.split(out_str)[0]):

            os.makedirs(os.path.split(out_str)[0])

        outfile = driver.Create(out_str, 100, 100, 1, gdal.GDT_Byte)

        outband = outfile.GetRasterBand(1)
        outband.WriteArray(mask, 0, 0)

        outband.FlushCache()

        geo = (self.chip_extents[chip].x_min, 30.0, 0.0, self.chip_extents[chip].y_max, 0.0, -30.0)

        outfile.SetGeoTransform(geo)
        outfile.SetProjection(WKT)

        src0, outfile = None, None

        return None

    def assemble_chips(self, chips):
        """

        :param chips: Path to the location of the chip masks
        :return:
        """

        # TODO composite chip arrays into a tile array, write tile array to raster

        pass

        infiles = glob.glob(chips + os.sep + "*.tif")

        driver = gdal.GetDriverByName("GTiff")

        mosaic = driver.Create(chips + os.sep + "mosaic.tif", 5000, 5000, 1, gdal.GDT_Byte)

        fill_ = np.zeros((5000,5000), dtype=np.uint8)

        for index, item in enumerate(infiles):

            pass

    def graph_results(self):

        # TODO produce graphs showing quantities w/o valid time segments for each Trends class

        pass


class CheckTimeSegments:

    def __init__(self, h, v, json_dir, out_dir):

        self.H = h
        self.V = v

        self.json_dir = json_dir

        self.out_dir = out_dir
        self.out_dir = self.out_dir + os.sep + "time_seg_masks"

        self.chip_info = ChipExtents(self.H, self.V)

        self.chip_extents = self.chip_info.CHIP_EXTENTS

        # self.json_tools = JSONReader(self.json_dir)

    def analyze_time_segments(self):

        json_reader = JSONReader(self.json_dir)

        counter = 1.0

        for chip in self.chip_extents:

            current = counter / 2500.0 * 100.0

            mask = np.zeros(shape=(100,100), dtype=np.uint8).flatten()

            json_results = json_reader.get_jsonchip(h=self.H, v=self.V, chip_coord=self.chip_extents[chip]).flatten()

            for index, result in enumerate(json_results):

                if len(result["change_models"]) > 0:

                    mask[index] = json_reader.check_time_segment(results=result)

                else:

                    # case for NoData within a tile
                    mask[index] = 0

            out_mask = mask.reshape((100,100))

            if np.any(out_mask):

                self.array_to_raster(chip=chip, mask=out_mask)

            sys.stdout.write("\r%s%% Done " % str(current)[:5])

            # needed to display the current percent complete
            sys.stdout.flush()

            counter += 1.0

        sys.stdout.flush()

        return None

    def array_to_raster(self, chip, mask):

        driver = gdal.GetDriverByName("GTiff")

        out_str = self.out_dir + "{a}chips{a}mask_{b}.tif".format(a=os.sep, b=chip)

        if not os.path.exists(os.path.split(out_str)[0]):

            os.makedirs(os.path.split(out_str)[0])

        outfile = driver.Create(out_str, 100, 100, 1, gdal.GDT_Byte)

        outband = outfile.GetRasterBand(1)

        outband.WriteArray(mask, 0, 0)

        outband.FlushCache()

        geo = (self.chip_extents[chip].x_min, 30.0, 0.0, self.chip_extents[chip].y_max, 0.0, -30.0)

        outfile.SetGeoTransform(geo)
        outfile.SetProjection(WKT)

        src0, outfile = None, None

        return None