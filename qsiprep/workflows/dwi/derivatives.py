"""
Writing outputs from a dwi preproc workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: init_dwi_derivatives_wf

"""

import os
import nibabel as nb
from nipype import logging
from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from ...interfaces import DerivativesDataSink
from ...engine import Workflow

DEFAULT_MEMORY_MIN_GB = 0.01
LOGGER = logging.getLogger('nipype.workflow')


def init_dwi_derivatives_wf(output_prefix,
                            source_file,
                            output_dir,
                            output_spaces,
                            template,
                            write_local_bvecs,
                            hmc_model,
                            shoreline_iters,
                            name='dwi_derivatives_wf'):
    """Set up a battery of datasinks to store derivatives in the right location.
    """
    workflow = Workflow(name=name)
    output_dir = str(output_dir)

    inputnode = pe.Node(
        niu.IdentityInterface(fields=[
            'source_file', 'dwi_t1', 'dwi_mask_t1', 'cnr_map_t1', 'bvals_t1', 'bvecs_t1',
            'local_bvecs_t1', 't1_b0_ref', 't1_b0_series', 'gradient_table_t1', 'dwi_mni',
            'dwi_mask_mni', 'cnr_map_mni', 'bvals_mni', 'bvecs_mni', 'local_bvecs_mni',
            'mni_b0_ref', 'mni_b0_series', 'gradient_table_mni', 'confounds',
            'hmc_optimization_data'
        ]),
        name='inputnode')

    if hmc_model == '3dSHORE' and shoreline_iters > 1:
        ds_optimization = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir, suffix='hmcOptimization'),
            name="ds_optimization", run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        workflow.connect([
            (inputnode, ds_optimization, [('hmc_optimization_data', 'in_file')])
        ])

    # Resample to T1w space
    if 'T1w' in output_spaces:
        # 4D DWI in t1 space
        ds_dwi_t1 = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space='T1w',
                desc='preproc',
                suffix='dwi',
                extension='.nii.gz',
                compress=True),
            name='ds_dwi_t1',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_bvals_t1 = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space='T1w',
                suffix='dwi',
                extension='.bval',
                desc='preproc'),
            name='ds_bvals_t1',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_bvecs_t1 = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space='T1w',
                suffix='dwi',
                extension='.bvec',
                desc='preproc'),
            name='ds_bvecs_t1',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_t1_b0_ref = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space='T1w',
                suffix='dwiref',
                extension='.nii.gz',
                compress=True),
            name='ds_t1_b0_ref',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_t1_b0_series = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space='T1w',
                suffix='b0series',
                extension='.nii.gz',
                compress=True),
            name='ds_t1_b0_series',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_dwi_mask_t1 = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space='T1w',
                desc='brain',
                suffix='mask',
                extension='.nii.gz',
                compress=True),
            name='ds_dwi_mask_t1',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_cnr_map_t1 = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space='T1w',
                desc=hmc_model,
                suffix='cnr',
                extension='.nii.gz',
                compress=True),
            name='ds_cnr_map_t1',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_gradient_table_t1 = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space='T1w',
                suffix='dwi',
                extension='.b',
                desc='preproc'),
            name='ds_gradient_table_t1',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)

        workflow.connect([
            (inputnode, ds_dwi_t1, [('dwi_t1', 'in_file')]),
            (inputnode, ds_bvals_t1, [('bvals_t1', 'in_file')]),
            (inputnode, ds_bvecs_t1, [('bvecs_t1', 'in_file')]),
            (inputnode, ds_t1_b0_ref, [('t1_b0_ref', 'in_file')]),
            (inputnode, ds_t1_b0_series, [('t1_b0_series', 'in_file')]),
            (inputnode, ds_dwi_mask_t1, [('dwi_mask_t1', 'in_file')]),
            (inputnode, ds_cnr_map_t1, [('cnr_map_t1', 'in_file')]),
            (inputnode, ds_gradient_table_t1, [('gradient_table_t1', 'in_file')])
            ])
        # If requested, write local bvecs
        if write_local_bvecs:
            ds_local_bvecs_t1 = pe.Node(
                DerivativesDataSink(
                    base_directory=output_dir,
                    source_file=source_file,
                    space='T1w',
                    suffix='bvec',
                    compress=True),
                name='ds_local_bvecs_t1',
                run_without_submitting=True,
                mem_gb=DEFAULT_MEMORY_MIN_GB)
            workflow.connect([(inputnode, ds_local_bvecs_t1, [('local_bvecs_t1', 'in_file')])])
    # Resample to template (default: MNI)
    if 'template' in output_spaces:
        # 4D DWI in t1 space
        ds_dwi_mni = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space=template,
                desc='preproc',
                suffix='dwi',
                extension='.nii.gz',
                keep_dtype=True,
                compress=True),
            name='ds_dwi_mni',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_bvals_mni = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space=template,
                suffix='dwi',
                extension='.bval',
                desc='preproc'),
            name='ds_bvals_mni',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_bvecs_mni = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space=template,
                suffix='dwi',
                extension='.bvec',
                desc='preproc'),
            name='ds_bvecs_mni',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_mni_b0_ref = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space=template,
                suffix='dwiref',
                extension='.nii.gz',
                compress=True),
            name='ds_mni_b0_ref',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_mni_b0_series = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space=template,
                suffix='b0series',
                extension='.nii.gz',
                compress=True),
            name='ds_mni_b0_series',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_dwi_mask_mni = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space=template,
                desc='brain',
                suffix='mask',
                extension='.nii.gz',
                compress=True),
            name='ds_dwi_mask_mni',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        ds_gradient_table_mni = pe.Node(
            DerivativesDataSink(
                prefix=output_prefix,
                source_file=source_file,
                base_directory=output_dir,
                space=template,
                suffix='dwi',
                extension='.b',
                desc='preproc'),
            name='ds_gradient_table_mni',
            run_without_submitting=True,
            mem_gb=DEFAULT_MEMORY_MIN_GB)
        workflow.connect([
            (inputnode, ds_dwi_mni, [('dwi_mni', 'in_file')]),
            (inputnode, ds_bvals_mni, [('bvals_mni', 'in_file')]),
            (inputnode, ds_bvecs_mni, [('bvecs_mni', 'in_file')]),
            (inputnode, ds_mni_b0_ref, [('mni_b0_ref', 'in_file')]),
            (inputnode, ds_mni_b0_series, [('mni_b0_series', 'in_file')]),
            (inputnode, ds_dwi_mask_mni, [('dwi_mask_mni', 'in_file')]),
            (inputnode, ds_gradient_table_mni, [('gradient_table_mni', 'in_file')])
            ])
        # Local bvecs?
        if write_local_bvecs:
            ds_local_bvecs_mni = pe.Node(
                DerivativesDataSink(
                    prefix=output_prefix,
                    source_file=source_file,
                    base_directory=output_dir,
                    space=template,
                    suffix='bvec',
                    compress=True),
                name='ds_local_bvecs_mni',
                run_without_submitting=True,
                mem_gb=DEFAULT_MEMORY_MIN_GB)
            workflow.connect([(inputnode, ds_local_bvecs_mni, [('local_bvecs_mni', 'in_file')])])
    return workflow
