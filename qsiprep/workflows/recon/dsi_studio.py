"""
DSI Studio workflows
^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: init_dsi_studio_recon_wf
.. autofunction:: init_dsi_studio_connectivity_wf
.. autofunction:: init_dsi_studio_export_wf

"""
import json
import nipype.pipeline.engine as pe
from nipype.interfaces import afni, utility as niu
from nipype.utils.filemanip import copyfile, split_filename
from qsiprep.interfaces.dsi_studio import (DSIStudioCreateSrc, DSIStudioGQIReconstruction,
                                           DSIStudioAtlasGraph, DSIStudioExport,
                                           FixDSIStudioExportHeader)

import logging
import os
import os.path as op
from qsiprep.interfaces.bids import ReconDerivativesDataSink
from qsiprep.interfaces.utils import GetConnectivityAtlases
from qsiprep.interfaces.connectivity import Controllability
from qsiprep.interfaces.gradients import RemoveDuplicates
from qsiprep.interfaces.mrtrix import ResponseSD, EstimateFOD, MRConvert

LOGGER = logging.getLogger('nipype.interface')
from .interchange import input_fields


def init_dsi_studio_recon_wf(name="dsi_studio_recon", output_suffix="", params={}):
    """Reconstructs diffusion data using DSI Studio.

    This workflow creates a ``.src.gz`` file from the input dwi, bvals and bvecs,
    then reconstructs ODFs using GQI.

    Inputs

        *Default qsiprep inputs*

    Outputs

        fibgz
            A DSI Studio fib file containing GQI ODFs, peaks and scalar values.

    Params

        ratio_of_mean_diffusion_distance: float
            Default 1.25. Distance to sample EAP at.

    """
    inputnode = pe.Node(niu.IdentityInterface(fields=input_fields),
                        name="inputnode")
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=['fibgz']),
        name="outputnode")
    workflow = pe.Workflow(name=name)
    create_src = pe.Node(DSIStudioCreateSrc(), name="create_src")
    gqi_recon = pe.Node(DSIStudioGQIReconstruction(), name="gqi_recon")
    # Resample anat mask
    resample_mask = pe.Node(
        afni.Resample(outputtype='NIFTI_GZ', resample_mode="NN"), name='resample_mask')

    workflow.connect([
        (inputnode, create_src, [('dwi_file', 'input_nifti_file'),
                                 ('bval_file', 'input_bvals_file'),
                                 ('bvec_file', 'input_bvecs_file')]),
        (inputnode, resample_mask, [('t1_brain_mask', 'in_file'),
                                    ('dwi_file', 'master')]),
        (create_src, gqi_recon, [('output_src', 'input_src_file')]),
        (resample_mask, gqi_recon, [('out_file', 'mask')]),
        (gqi_recon, outputnode, [('output_fib', 'fibgz')])
    ])

    if output_suffix:
        # Save the output in the outputs directory
        ds_gqi_fibgz = pe.Node(
            ReconDerivativesDataSink(
                extension='.fib.gz',
                suffix=output_suffix,
                compress=True),
            name='ds_gqi_fibgz',
            run_without_submitting=True)
        workflow.connect(gqi_recon, 'output_fib', ds_gqi_fibgz, 'in_file')
    return workflow


def init_dsi_studio_connectivity_wf(name="dsi_studio_connectivity", n_procs=1,
                                    params={}, output_suffix=""):
    """Calculate streamline-based connectivity matrices using DSI Studio.

    DSI Studio has a deterministic tractography algorithm that can be used to
    estimate pairwise regional connectivity. It calculates multiple connectivity
    measures.

    Inputs

        fibgz
            A DSI Studio fib file produced by DSI Studio reconstruction.

    Outputs

        matfile
            A MATLAB-format file with numerous connectivity matrices for each
            atlas.

    Params

        fiber_count
            number of streamlines to generate. Cannot also specify seed_count
        seed_count
            Number of seeds to track from. Does not guarantee a fixed number of
            streamlines and cannot be used with the fiber_count option.
        method
            0: streamline (Euler) 4: Runge Kutta
        seed_plan
            0: = traits.Enum((0, 1), argstr="--seed_plan=%d")
        initial_dir
            Seeds begin oriented as 0: the primary orientation of the ODF 1: a random orientation
            or 2: all orientations
        connectivity_type
            "pass" to count streamlines passing through a region. "end" to force
            streamlines to terminate in regions they count as connecting.
        connectivity_value
            "count", "ncount", "fa" used to quantify connection strength.
        random_seed
            Setting to True generates truly random (not-reproducible) seeding.
        fa_threshold
            If not specified, will use the DSI Studio Otsu threshold. Otherwise
            specigies the minimum qa value per fixed to be used for tracking.
        step_size
            Streamline propagation step size in millimeters.
        turning_angle
            Maximum turning angle in degrees for steamline propagation.
        smoothing
            DSI Studio smoothing factor
        min_length
            Minimum streamline length in millimeters.
        max_length
            Maximum streamline length in millimeters.

    """
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=input_fields + ['fibgz', 'atlas_configs']),
        name="inputnode")
    outputnode = pe.Node(niu.IdentityInterface(fields=['matfile']),
                         name="outputnode")
    workflow = pe.Workflow(name=name)
    calc_connectivity = pe.Node(DSIStudioAtlasGraph(n_procs=n_procs, **params),
                                name='calc_connectivity')
    workflow.connect([
        (inputnode, calc_connectivity, [('atlas_configs', 'atlas_configs'),
                                        ('fibgz', 'input_fib')]),
        (calc_connectivity, outputnode, [('connectivity_matfile', 'matfile')])
    ])
    if output_suffix:
        # Save the output in the outputs directory
        ds_connectivity = pe.Node(ReconDerivativesDataSink(suffix=output_suffix),
                                  name='ds_' + name,
                                  run_without_submitting=True)
        workflow.connect(calc_connectivity, 'connectivity_matfile', ds_connectivity, 'in_file')
    return workflow


def init_dsi_studio_export_wf(name="dsi_studio_export", params={}, output_suffix=""):
    """Export scalar maps from a DSI Studio fib file into NIfTI files with correct headers.

    This workflow exports gfa, fa0, fa1, fa2 and iso.

    Inputs

        fibgz
            A DSI Studio fib file

    Outputs

        gfa
            NIfTI file containing generalized fractional anisotropy (GFA).
        fa0
            Quantitative Anisotropy for the largest fixel in each voxel.
        fa1
            Quantitative Anisotropy for the second-largest fixel in each voxel.
        fa2
            Quantitative Anisotropy for the third-largest fixel in each voxel.
        iso
            Isotropic component of the ODF in each voxel.

    """
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=input_fields + ['fibgz']),
        name="inputnode")
    outputnode = pe.Node(
        niu.IdentityInterface(fields=['gfa', 'fa0', 'fa1', 'fa2', 'iso']),
        name="outputnode")
    workflow = pe.Workflow(name=name)
    export = pe.Node(DSIStudioExport(to_export="gfa,fa0,fa1,fa2,fa3,iso"), name='export')
    fixhdr_nodes = {}
    for scalar_name in ['gfa', 'fa0', 'fa1', 'fa2', 'iso']:
        output_name = scalar_name + '_file'
        fixhdr_nodes[scalar_name] = pe.Node(FixDSIStudioExportHeader(), name='fix_'+scalar_name)
        connections = [(export, fixhdr_nodes[scalar_name], [(output_name, 'dsi_studio_nifti')]),
                       (inputnode, fixhdr_nodes[scalar_name], [('dwi_file',
                                                                'correct_header_nifti')]),
                       (fixhdr_nodes[scalar_name], outputnode, [('out_file', scalar_name)])]
        if output_suffix:
            connections += [(fixhdr_nodes[scalar_name],
                             pe.Node(
                                 ReconDerivativesDataSink(desc=scalar_name,
                                                          suffix=output_suffix),
                                 name='ds_%s_%s' % (name, scalar_name)),
                             [('out_file', 'in_file')])]
        workflow.connect(connections)

    workflow.connect([(inputnode, export, [('fibgz', 'input_file')])])

    return workflow
