
"""Handle merging and spliting of DSI files."""
import subprocess
import logging
import gzip
import re
import os
import os.path as op
import numpy as np
import nibabel as nb
try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO
from nipype.interfaces.base import (BaseInterfaceInputSpec, TraitedSpec, File, SimpleInterface,
                                    traits, isdefined)
from nipype.utils.filemanip import fname_presuffix
from dipy.core.geometry import cart2sphere
from dipy.direction import peak_directions
from dipy.core.sphere import HemiSphere
from scipy.io.matlab import loadmat, savemat
from pkg_resources import resource_filename as pkgr


LOGGER = logging.getLogger('nipype.workflow')
ODF_COLS = 20000  # Number of columns in DSI Studio odf split
MIN_NONZERO = 1e-6


class FODtoFIBGZInputSpec(BaseInterfaceInputSpec):
    mif_file = File(exists=True, mandatory=True)
    mask_file = File(exists=True)
    num_fibers = traits.Int(5, usedefault=True)
    unit_odf = traits.Bool(False, usedefault=True)
    fib_file = File()


class FODtoFIBGZOutputSpec(TraitedSpec):
    fib_file = File(exists=True)


class FODtoFIBGZ(SimpleInterface):
    input_spec = FODtoFIBGZInputSpec
    output_spec = FODtoFIBGZOutputSpec

    def _run_interface(self, runtime):
        mif_file = self.inputs.mif_file
        mask_file = self.inputs.mask_file
        if isdefined(self.inputs.fib_file):
            output_fib_file = self.inputs.fib_file
            if output_fib_file.endswith(".gz"):
                output_fib_file = output_fib_file[:-3]
        else:
            output_fib_file = fname_presuffix(mif_file, newpath=runtime.cwd, suffix=".fib",
                                              use_ext=False)

        verts, faces = get_dsi_studio_ODF_geometry("odf8")
        num_dirs, _ = verts.shape
        hemisphere = num_dirs // 2
        x, y, z = verts[:hemisphere].T
        _, theta, phi = cart2sphere(x, y, -z)
        dirs_txt = op.join(runtime.cwd, "directions.txt")
        np.savetxt(dirs_txt, np.column_stack([phi, theta]))

        odf_amplitudes_nii = op.join(runtime.cwd, "amplitudes.nii")
        popen_run(["sh2amp", "-quiet", "-nonnegative", mif_file, dirs_txt, odf_amplitudes_nii])

        if not op.exists(odf_amplitudes_nii):
            raise FileNotFoundError("Unable to create %s", odf_amplitudes_nii)
        amplitudes_img = nb.load(odf_amplitudes_nii)

        if isdefined(mask_file):
            mask_img = nb.load(mask_file)
        else:
            ampl_data = amplitudes_img.get_data()
            ampl_mask = ampl_data.sum(3) > 1e-6
            mask_img = nb.Nifti1Image(ampl_mask.astype(np.float),
                                      amplitudes_img.affine)

        self._results['fib_file'] = output_fib_file
        amplitudes_to_fibgz(amplitudes_img, verts, faces, output_fib_file, mask_img,
                            num_fibers=self.inputs.num_fibers,
                            unit_odf=self.inputs.unit_odf)
        os.remove("amplitudes.nii")
        return runtime


class FIBGZtoFODInputSpec(BaseInterfaceInputSpec):
    fib_file = File(exists=True, mandatory=True)
    ref_image = File(exists=True, mandatory=True)
    subtract_iso = traits.Bool(True, usedefault=True)
    mif_file = File()


class FIBGZtoFODOutputSpec(TraitedSpec):
    mif_file = File(exists=True)


class FIBGZtoFOD(SimpleInterface):
    input_spec = FIBGZtoFODInputSpec
    output_spec = FIBGZtoFODOutputSpec

    def _run_interface(self, runtime):
        fib_file = self.inputs.fib_file
        if isdefined(self.inputs.mif_file):
            output_mif_file = self.inputs.mif_file
        else:
            output_mif_file = fname_presuffix(fib_file, newpath=runtime.cwd, suffix=".mif",
                                              use_ext=False)
        fibmat = fast_load_fibgz(fib_file)
        dims = tuple(fibmat['dimension'].squeeze().astype(np.int))
        directions = fibmat['odf_vertices'].T

        odf_vars = [k for k in fibmat.keys() if re.match("odf\\d+", k)]
        valid_odfs = []
        flat_mask = fibmat["fa0"].squeeze() > 0
        n_voxels = np.prod(dims)
        for n in range(len(odf_vars)):
            varname = "odf%d" % n
            odfs = fibmat[varname]
            odf_sum = odfs.sum(0)
            odf_sum_mask = odf_sum > 0
            valid_odfs.append(odfs[:, odf_sum_mask].T)
        odf_array = np.row_stack(valid_odfs)
        if self.inputs.subtract_iso:
            odf_array = odf_array - odf_array.min(0)

        # Convert each column to a 3d file, then concatenate them
        odfs_3d = []
        for odf_vals in odf_array.T:
            new_data = np.zeros(n_voxels, dtype=np.float32)
            new_data[flat_mask] = odf_vals
            odfs_3d.append(new_data.reshape(dims, order="F"))

        real_img = nb.load(self.inputs.ref_image)
        odf4d = np.stack(odfs_3d, -1)
        odf4d_img = nb.Nifti1Image(odf4d, real_img.affine, real_img.header)
        odf_values_file = op.join(runtime.cwd, "odf_values.nii")
        odf4d_img.to_filename(odf_values_file)

        num_dirs, _ = directions.shape
        hemisphere = num_dirs // 2
        x, y, z = directions[:hemisphere].T
        _, theta, phi = cart2sphere(-x, -y, z)
        dirs_txt = op.join(runtime.cwd, "ras+directions.txt")
        np.savetxt(dirs_txt, np.column_stack([phi, theta]))

        popen_run(["amp2sh", "-quiet", "-force", "-directions", dirs_txt, "odf_values.nii",
                   output_mif_file])
        os.remove(odf_values_file)
        os.remove(dirs_txt)
        self._results['mif_file'] = output_mif_file
        return runtime


def get_dsi_studio_ODF_geometry(odf_key):
    mat_path = pkgr('qsiprep', 'data/odfs.mat')
    m = loadmat(mat_path)
    odf_vertices = m[odf_key + "_vertices"].T
    odf_faces = m[odf_key + "_faces"].T
    return odf_vertices, odf_faces


def popen_run(arg_list):
    cmd = subprocess.Popen(arg_list, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    out, err = cmd.communicate()
    LOGGER.info(out)
    LOGGER.info(err)


def amplitudes_to_fibgz(amplitudes_img, odf_dirs, odf_faces, output_file,
                        mask_img, num_fibers=5, unit_odf=False):
    """Convert a NiftiImage of ODF amplitudes to a DSI Studio fib file.

    Parameters:
    ===========

    amplitudes_img: nb.Nifti1Image
        4d NIfTI image that contains amplitudes for the ODFs
    odf_dirs: np.ndarray
        N x 3 array containing the directions corresponding to the
        amplitudes in ``amplitudes_img``. The values in
        ``amplitudes_img.get_data()[..., i]`` are for the
        direction in ``odf_dirs[i]``.
    odf_faces: np.ndarray
        triangles connecting the vertices in ``odf_dirs``
    output_file: str
        Path where the output fib file will be written.
    mask_img: nb.Nifti1Image
        3d Image that is nonzero where voxels contain brain.
    num_fibers: int
        The maximum number of fibers/fixels stored in each voxel.

    Returns:
    ========

    None


    """
    num_dirs, _ = odf_dirs.shape
    hemisphere = num_dirs // 2
    x, y, z = odf_dirs[:hemisphere].T
    hs = HemiSphere(x=x, y=y, z=z)

    if not np.allclose(mask_img.affine, amplitudes_img.affine):
        raise ValueError("Differing orientation between mask and amplitudes")
    if not mask_img.shape == amplitudes_img.shape[:3]:
        raise ValueError("Differing grid between mask and amplitudes")

    # Get the flat mask
    ampl_data = amplitudes_img.get_data()
    flat_mask = mask_img.get_data().flatten(order="F") > 0
    odf_array = ampl_data.reshape(-1, ampl_data.shape[3], order='F')
    del ampl_data
    masked_odfs = odf_array[flat_mask, :]
    z0 = np.nanmax(masked_odfs)
    masked_odfs = masked_odfs / z0
    masked_odfs[masked_odfs < 0] = 0
    masked_odfs = np.nan_to_num(masked_odfs).astype(np.float)

    if unit_odf:
        sums = masked_odfs.sum(1)
        sums[sums == 0] = 1
        masked_odfs = np.masked_odfs / sums[:, np.newaxis]

    n_odfs = masked_odfs.shape[0]
    peak_indices = np.zeros((n_odfs, num_fibers))
    peak_vals = np.zeros((n_odfs, num_fibers))

    dsi_mat = {}
    # Create matfile that can be read by dsi Studio
    dsi_mat['dimension'] = np.array(amplitudes_img.shape[:3])
    dsi_mat['voxel_size'] = np.array(amplitudes_img.header.get_zooms()[:3])
    n_voxels = int(np.prod(dsi_mat['dimension']))
    LOGGER.info("Detecting Peaks")
    for odfnum in range(n_odfs):
        dirs, vals, indices = peak_directions(masked_odfs[odfnum], hs)
        for dirnum, (val, idx) in enumerate(zip(vals, indices)):
            if dirnum == num_fibers:
                break
            peak_indices[odfnum, dirnum] = idx
            peak_vals[odfnum, dirnum] = val

    # ensure that fa0 > 0 for all odf values
    peak_vals[np.abs(peak_vals[:, 0]) < MIN_NONZERO, 0] = MIN_NONZERO
    for nfib in range(num_fibers):
        # fill in the "fa" values
        fa_n = np.zeros(n_voxels)
        fa_n[flat_mask] = peak_vals[:, nfib]
        dsi_mat['fa%d' % nfib] = fa_n.astype(np.float32)

        # Fill in the index values
        index_n = np.zeros(n_voxels)
        index_n[flat_mask] = peak_indices[:, nfib]
        dsi_mat['index%d' % nfib] = index_n.astype(np.int16)

    # Add in the ODFs
    num_odf_matrices = n_odfs // ODF_COLS
    split_indices = (np.arange(num_odf_matrices) + 1) * ODF_COLS
    odf_splits = np.array_split(masked_odfs, split_indices, axis=0)
    for splitnum, odfs in enumerate(odf_splits):
        dsi_mat['odf%d' % splitnum] = odfs.T.astype(np.float32)

    dsi_mat['odf_vertices'] = odf_dirs.T
    dsi_mat['odf_faces'] = odf_faces.T
    dsi_mat['z0'] = np.array([z0])
    savemat(output_file, dsi_mat, format='4', appendmat=False)


def amplitudes_to_sh_mif(amplitudes_img, odf_dirs, output_file, working_dir):
    """Convert an image of ODF amplitudes to a MRtrix sh mif file.

    Parameters:
    ============

    amplitudes_img: nb.Nifti1Image
        4d NIfTI image that contains amplitudes for the ODFs
    odf_dirs: np.ndarray
        2*N x 3 array containing the directions corresponding to the
        amplitudes in ``amplitudes_img``. The values in
        ``amplitudes_img.get_data()[..., i]`` are for the
        direction in ``odf_dirs[i]``. Here the second half of the
        directions are the opposite of the fist and therefore have the
        same amplitudes.
    output_file: str
        Path where the output ``.mif`` file will be written.
    working_dir: str
        Path where temp files will be written to

    Returns:
    ========

    None

    """
    temp_nii = op.join(working_dir, "odf_values.nii")
    amplitudes_img.to_filename(temp_nii)

    num_dirs, _ = odf_dirs.shape
    hemisphere = num_dirs // 2
    x, y, z = odf_dirs[:hemisphere].T
    _, theta, phi = cart2sphere(-x, -y, z)
    dirs_txt = op.join(working_dir, "ras+directions.txt")
    np.savetxt(dirs_txt, np.column_stack([phi, theta]))

    popen_run(["amp2sh", "-quiet", "-force", "-directions", dirs_txt, "odf_values.nii",
               output_file])
    os.remove(temp_nii)
    os.remove(dirs_txt)


def fast_load_fibgz(fib_file):
    """Load a potentially gzipped fibgz file more quickly than using built-in gzip.
    """
    # Try to load a non-zipped file
    if not fib_file.endswith("gz"):
        return loadmat(fib_file)

    # Load a zipped file quickly if possible
    def find_zcat():
        def is_exe(fpath):
            return os.path.exists(fpath) and os.access(fpath, os.X_OK)
        for program in ["gzcat", "zcat"]:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return program
        return None

    # Check if a zcat is available on this system:
    zcatter = find_zcat()
    if zcatter is not None:
        p = subprocess.Popen([zcatter, fib_file], stdout=subprocess.PIPE)
        fh = StringIO(p.communicate()[0])
        assert p.returncode == 0
        return loadmat(fh)

    with gzip.open(fib_file, "r") as f:
        LOGGER.info("Loading with python gzip. To load faster install zcat or gzcat.")
        return loadmat(f)
