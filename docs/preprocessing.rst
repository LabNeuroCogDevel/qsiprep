.. include:: links.rst

.. _preprocessing:

Preprocessing
=========================

There are some important considerations for how your diffusion data will be preprocessed.

  1. You must choose how to combine dwi scans within a session (:ref:`merging`)
  2. How to correct for susceptibility distortion.
  3. How to perform motion correction

Building a pipeline
--------------------

.. _merging:

Merging multiple scans from a session
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For q-space imaging sequences it is common to have multiple separate scans to
acquire the entire sampling scheme. These scans get aligned and merged into
a single DWI series before reconstruction. It is also common to collect
a DWI scan (or scans) in the reverse phase encoding direction to use for
susceptibility distortion correction (SDC).

This creates a number of possible scenarios for preprocessing your DWIs. These
scenarios can be controlled by the ``combine_all_dwis`` argument. If your study
has multiple sessions, DWI scans will *never* be combined across sessions.
Merging only occurs within a session.

If ``combine_all_dwis`` is ``False`` (not present in the commandline call), each dwi
scan in the ``dwi`` directories will be processed independently. You will have one
preprocessed output per each DWI file in your input.

If ``combine_all_dwis`` is set to ``True``, two possibilities arise. If all DWIs in a session
are in the same PE direction, they will be merged into a single series. If there are
two PE directions detected in the DWI scans and ``'fieldmaps'`` is not in ``ignore``,
images are combined according to their PE direction, and their b0 reference images are used to
perform SDC.

If you have some scans you want to combine and others you want to preprocess separately,
consider creating fake sessions in your BIDS directory.


Susceptibility correction methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The are three kinds of SDC available in qsiprep:

  1. :ref:`sdc_pepolar` (also called **blip-up/blip-down**):
     This is the implementation from FMRIPREP, using 3dQwarp to
     correct a DWI series using a fieldmap in the fmaps directory [Jezzard1995]_.
     The reverse phase encoding direction scan can come from the fieldmaps directory
     or the dwi directory.

  2. :ref:`sdc_phasediff`: Use a B0map sequence that includes at lease one magnitude
     image and two phase images or a phasediff image.

  3. :ref:`sdc_fieldmapless`: The SyN-based susceptibility distortion correction
     implemented in FMRIPREP. To use this method, include argument --use-syn-sdc when
     calling qsiprep. Briefly, this method estimates a SDC warp using ANTS SyN based
     on an average fieldmap in MNI space. For details on this method, see
     `fmriprep's documentation <https://fmriprep.readthedocs.io/en/latest/api/index.html#sdc-fieldmapless>`_


``qsiprep`` determines if a fieldmap should be used based on the ``"IntendedFor"``
fields in the JSON sidecars in the ``fmap/`` directory. If you have two DWI
series with reverse phase encodings, but would rather use method 1 instead of
1a, include the ``--prefer-dedicated-fmaps`` argument.

.. warning::
   if you are using ``eddy`` as the head motion correction method, the fieldmap will be
   converted to a format that can be used with ``eddy``. Methods 1 and 2 work with ``eddy``
   and all methods work with SHORELine.


.. _outputs:

Outputs of qsiprep
-------------------

qsiprep generates three broad classes of outcomes:

  1. **Visual QA (quality assessment) reports**:
     one :abbr:`HTML (hypertext markup language)` per subject,
     depicting images that provide a sanity check for each step of the pipeline.

  2. **Pre-processed imaging data** such as anatomical segmentations, realigned and resampled
     diffusion weighted images and the corresponding corrected gradient files in FSL and MRTrix
     format.

  3. **Additional data for subsequent analysis**, for instance the transformations
     between different spaces or the estimated head motion and model fit quality calculated
     during model-based head motion correction.


Visual Reports
^^^^^^^^^^^^^^^

qsiprep outputs summary reports, written to ``<output dir>/qsiprep/sub-<subject_label>.html``.
These reports provide a quick way to make visual inspection of the results easy.  One useful
graphic is the animation of the q-space sampling scheme before and after the pipeline. Here is
a sampling scheme from a DSI scan:

.. figure:: _static/sampling_scheme.gif
    :scale: 75%

    A Q5 DSI sampling scheme before (left) and after (right) preprocessing. This is useful to
    confirm that the gradients have indeed been rotated and that head motion correction has not
    disrupted the scheme extensively.


Preprocessed data (qsiprep *derivatives*)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are additional files, called "Derivatives", written to
``<output dir>/qsiprep/sub-<subject_label>/``.

Derivatives related to T1w files are nearly identical to those produced by ``FMRIPREP`` and
can be found in the ``anat`` subfolder:

- ``*T1w_brainmask.nii.gz`` Brain mask derived using ANTs' ``antsBrainExtraction.sh``.
- ``*T1w_class-CSF_probtissue.nii.gz``
- ``*T1w_class-GM_probtissue.nii.gz``
- ``*T1w_class-WM_probtissue.nii.gz`` tissue-probability maps.
- ``*T1w_dtissue.nii.gz`` Tissue class map derived using FAST.
- ``*T1w_preproc.nii.gz`` Bias field corrected T1w file, using ANTS' N4BiasFieldCorrection
- ``*T1w_space-MNI152NLin2009cAsym_brainmask.nii.gz`` Same as ``_brainmask`` above, but in MNI space.
- ``*T1w_space-MNI152NLin2009cAsym_class-CSF_probtissue.nii.gz``
- ``*T1w_space-MNI152NLin2009cAsym_class-GM_probtissue.nii.gz``
- ``*T1w_space-MNI152NLin2009cAsym_class-WM_probtissue.nii.gz`` Probability tissue maps, transformed into MNI space
- ``*T1w_space-MNI152NLin2009cAsym_dtissue.nii.gz`` Same as ``_dtissue`` above, but in MNI space
- ``*T1w_space-MNI152NLin2009cAsym_preproc.nii.gz`` Same as ``_preproc`` above, but in MNI space
- ``*T1w_space-MNI152NLin2009cAsym_target-T1w_warp.h5`` Composite (warp and affine) transform to map from MNI to T1 space
- ``*T1w_target-MNI152NLin2009cAsym_warp.h5`` Composite (warp and affine) transform to transform T1w into MNI space

.. Note:
  These are in LPS+ orientation, so are not identical to FMRIPREP's anatomical outputs

Derivatives related to diffusion images are in the ``dwi`` subfolder.

- ``*_confounds.tsv`` A tab-separated value file with one column per calculated confound and one row per timepoint/volume

Volumetric output spaces include ``T1w`` (default) and ``MNI152NLin2009cAsym``.

- ``*dwiref.nii.gz`` The b0 template
- ``*desc-brain_mask.nii.gz`` The generous brain mask that should be reduced probably
- ``*desc-preproc_dwi.nii.gz`` Resampled DWI series including all b0 images.
- ``*desc-preproc_dwi.bval``, ``*desc-preproc_dwi.bvec`` FSL-style bvals and bvecs files.
  *These will be incorrectly interpreted by MRTrix, but will work with DSI Studio.* Use the
  ``.b`` file for MRTrix.
- ``desc-preproc_dwi.b`` The gradient table to import data into MRTrix. This and the
  ``_dwi.nii.gz`` can be converted directly to a ``.mif`` file using the ``mrconvert -grad _dwi.b``
  command.
- ``*b0series.nii.gz`` The b0 images from the series in a 4d image. Useful to see how much the
  images are impacted by Eddy currents.
- ``*bvecs.nii.gz`` Each voxel contains a gradient table that has been adjusted for local
  rotations introduced by spatial warping.
- ``*cnr.nii.gz`` Each voxel contains a contrast-to-noise model defined as the variance of the
  signal model divided by the variance of the error of the signal model.


.. _dwi_confounds:

Confounds
^^^^^^^^^^^^

See implementation on :mod:`~qsiprep.workflows.dwi.confounds.init_dwi_confs_wf`.


For each DWI processed by qsiprep, a
``<output_folder>/qsiprep/sub-<sub_id>/func/sub-<sub_id>_task-<task_id>_run-<run_id>_confounds.tsv``
file will be generated.
These are :abbr:`TSV (tab-separated values)` tables, which look like the example below::

  framewise_displacement	trans_x	trans_y	trans_z	rot_x	rot_y	rot_z	hmc_r2	hmc_xcorr	original_file	grad_x	grad_y	grad_z	bval

  n/a    -0.705	-0.002	0.133	0.119	0.350	0.711	0.941	0.943	sub-abcd_dwi.nii.gz	0.000	0.000	0.000	0.000
  16.343	-0.711	-0.075	0.220	0.067	0.405	0.495	0.945	0.946	sub-abcd_dwi.nii.gz	0.000	0.000	0.000	0.000
  35.173	-0.672	-0.415	0.725	0.004	0.468	1.055	0.756	0.766	sub-abcd_dwi.nii.gz	-0.356	0.656	0.665	3000.000
  45.131	0.021	-0.498	1.046	0.403	0.331	1.400	0.771	0.778	sub-abcd_dwi.nii.gz	-0.935	0.272	0.229	3000.000
  37.506	-0.184	0.117	0.723	0.305	0.138	0.964	0.895	0.896	sub-abcd_dwi.nii.gz	-0.187	-0.957	-0.223	2000.000
  16.388	-0.447	0.020	0.847	0.217	0.129	0.743	0.792	0.800	sub-abcd_dwi.nii.gz	-0.111	-0.119	0.987	3000.000

The motion parameters come from the model-based head motion estimation workflow. The ``hmc_r2`` and
``hmc_xcorr`` are whole-brain r^2 values and cross correlation scores (using the ANTs definition)
between the model-generated target image and the motion-corrected empirical image. The final
columns are not really confounds, but book-keeping information that reminds us which 4d DWI series
the image originally came from and what gradient direction (``grad_x``, ``grad_y``, ``grad_z``)
and gradient strength ``bval`` the image came from. This can be useful for tracking down
mostly-corrupted scans and can indicate if the head motion model isn't working on specific
gradient strengths or directions.

Confounds and "carpet"-plot on the visual reports
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

fMRI has been using a "carpet" visualization of the
:abbr:`DWI (blood-oxygen level-dependent)` time-series (see [Power2016]_),
but this type of plot does not make sense for DWI data. Instead, we plot
the cross-correlation value between each raw slice and the HMC model signal
resampled into that slice.
This plot is included for each run within the corresponding visual report.
An example of these plots follows:


.. figure:: _static/sub-abcd_carpetplot.svg
    :scale: 100%

    Higher scores appear more yellow, while lower scores
    are more blue. Not all slices contain the same number of voxels,
    so the number of voxels in the slice is represented in the color bar
    to the left of the image plot. The more yellow the pixel, the more
    voxels are present in the slice. Purple pixels reflect slices with fewer
    brain voxels.



Preprocessing pipeline details
---------------------------------

``qsiprep`` adapts its pipeline depending on what data and metadata are
available and are used as the input.


T1w/T2w preprocessing
^^^^^^^^^^^^^^^^^^^^^^^^

:mod:`qsiprep.workflows.anatomical.init_anat_preproc_wf`

.. workflow::
    :graph2use: orig
    :simple_form: yes

    from qsiprep.workflows.anatomical import init_anat_preproc_wf
    wf = init_anat_preproc_wf(omp_nthreads=1,
                              reportlets_dir='.',
                              output_dir='.',
                              template='MNI152NLin2009cAsym',
                              output_spaces=['T1w', 'fsnative',
                                             'template', 'fsaverage5'],
                              output_resolution=1.25,
                              skull_strip_template='OASIS',
                              force_spatial_normalization=True,
                              freesurfer=True,
                              longitudinal=False,
                              debug=False,
                              hires=True,
                              num_t1w=1)


The anatomical sub-workflow begins by constructing an average image by
:ref:`conforming <conformation>` all found T1w images to LPS orientation and
a common voxel size, and, in the case of multiple images, averages them into a
single reference template (see `Longitudinal processing`_).

.. _t1preproc_steps:

Brain extraction, brain tissue segmentation and spatial normalization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Then, the T1w image/average is skull-stripped using ANTs' ``antsBrainExtraction.sh``,
which is an atlas-based brain extraction workflow.

.. figure:: _static/brainextraction_t1.svg
    :scale: 100%

    Brain extraction


Once the brain mask is computed, FSL ``fast`` is utilized for brain tissue segmentation.

.. figure:: _static/segmentation.svg
    :scale: 100%

    Brain tissue segmentation.


Finally, spatial normalization to MNI-space is performed using ANTs' ``antsRegistration``
in a multiscale, mutual-information based, nonlinear registration scheme.
In particular, spatial normalization is done using the `ICBM 2009c Nonlinear
Asymmetric template (1×1×1mm) <http://nist.mni.mcgill.ca/?p=904>`_ [Fonov2011]_.

When processing images from patients with focal brain lesions (e.g. stroke, tumor
resection), it is possible to provide a lesion mask to be used during spatial
normalization to MNI-space [Brett2001]_.
ANTs will use this mask to minimize warping of healthy tissue into damaged
areas (or vice-versa).
Lesion masks should be binary NIfTI images (damaged areas = 1, everywhere else = 0)
in the same space and resolution as the T1 image, and follow the naming convention specified in
`BIDS Extension Proposal 3: Common Derivatives <https://docs.google.com/document/d/1Wwc4A6Mow4ZPPszDIWfCUCRNstn7d_zzaWPcfcHmgI4/edit#heading=h.9146wuepclkt>`_
(e.g. ``sub-001_T1w_label-lesion_roi.nii.gz``).
This file should be placed in the ``sub-*/anat`` directory of the BIDS dataset
to be run through ``qsiprep``.

.. figure:: _static/T1MNINormalization.svg
    :scale: 100%

    Animation showing T1w to MNI normalization


Longitudinal processing
~~~~~~~~~~~~~~~~~~~~~~~~~~

In the case of multiple T1w images (across sessions and/or runs), T1w images are
merged into a single template image using FreeSurfer's ``mri_robust_template``.
This template may be *unbiased*, or equidistant from all source images, or
aligned to the first image (determined lexicographically by session label).
For two images, the additional cost of estimating an unbiased template is
trivial and is the default behavior, but, for greater than two images, the cost
can be a slowdown of an order of magnitude.
Therefore, in the case of three or more images, ``qsiprep`` constructs
templates aligned to the first image, unless passed the ``--longitudinal``
flag, which forces the estimation of an unbiased template.

.. note::

    The preprocessed T1w image defines the ``T1w`` space.
    In the case of multiple T1w images, this space may not be precisely aligned
    with any of the original images.
    Reconstructed surfaces and functional datasets will be registered to the
    ``T1w`` space, and not to the input images.


DWI preprocessing
^^^^^^^^^^^^^^^^^^^^

:mod:`qsiprep.workflows.dwi.base.init_dwi_preproc_wf`

.. workflow::
    :graph2use: orig
    :simple_form: yes

    from qsiprep.workflows.dwi.base import init_dwi_preproc_wf
    wf = init_dwi_preproc_wf({'dwi_series': ['fake.nii'],
                              'fieldmap_info': {'suffix': None},
                              'dwi_series_pedir': 'j'},
                              output_prefix='',
                              ignore=[],
                              b0_threshold=100,
                              motion_corr_to='iterative',
                              b0_to_t1w_transform='Rigid',
                              hmc_model='3dSHORE',
                              hmc_transform='Rigid',
                              shoreline_iters=2,
                              impute_slice_threshold=0,
                              eddy_config=None,
                              reportlets_dir='.',
                              output_spaces=['T1w', 'template'],
                              dwi_denoise_window=5,
                              denoise_before_combining=True,
                              template='MNI152NLin2009cAsym',
                              output_dir='.',
                              omp_nthreads=1,
                              fmap_bspline=False,
                              fmap_demean=True,
                              use_syn=True,
                              force_syn=False,
                              low_mem=False,
                              sloppy=True,
                              layout=None)


Preprocessing of :abbr:`DWI (Diffusion Weighted Image)` files is
split into multiple sub-workflows described below.

.. _dwi_hmc:

Head-motion estimation (SHORELine)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:mod:`qsiprep.workflows.dwi.hmc.init_dwi_hmc_wf`

.. workflow::
    :graph2use: colored
    :simple_form: yes

    from qsiprep.workflows.dwi.hmc_sdc import init_qsiprep_hmcsdc_wf
    wf = init_qsiprep_hmcsdc_wf({'dwi_series':['dwi1.nii', 'dwi2.nii'],
                                'fieldmap_info': {'suffix': None},
                                'dwi_series_pedir': 'j'},
                                hmc_transform='Affine',
                                hmc_model='3dSHORE',
                                hmc_align_to='iterative',
                                template='MNI152NLin2009cAsym',
                                shoreline_iters=1,
                                impute_slice_threshold=0,
                                omp_nthreads=1,
                                fmap_bspline=False,
                                fmap_demean=False,
                                use_syn=True,
                                force_syn=False,
                                name='qsiprep_hmcsdc_wf',
                                dwi_metadata={})


A long-standing issue for q-space imaging techniques, particularly DSI, has
been the lack of motion correction methods. DTI and multi-shell HARDI have
had ``eddy_correct`` and ``eddy`` in FSL, but DSI has relied on aligning the
interleaved b0 images and applying the transforms to nearby non-b0 images.

``qsiprep`` introduces a method for head motion correction that iteratively
creates target images based on ``3dSHORE`` or ``MAPMRI`` fits.
First, all b0 images are aligned to a midpoint b0 image (or the first b0 image
if ``hmc_align_to="first"``) and each non-b0 image is transformed along with
its nearest b0 image.

Then, for each non-b0 image, a ``3dSHORE`` or ``MAPMRI``
model is fit to all the other images with that image left out. The model is then
used to generate a target signal image for the gradient direction and magnitude
(i.e. q-space coordinate) of the left-out image. The left-out image is registered
to the generated target
signal image and its vector is rotated accordingly. A new model is fit on the
transformed images and their rotated vectors. The leave-one-out procedure is
then repeated on this updated DWI and gradient set.

If ``"none"`` is specified as the hmc_model, then only the b0 images are used
and the non-b0 images are transformed based on their nearest b0 image. This
is probably not a great idea.

Susceptibility distortion correction is run as part of this pipeline to be
consistent with the ``TOPUP``/``eddy`` workflow.

Ultimately a list of 6 (or 12)-parameters per time-step is written and
fed to the :ref:`confounds workflow <dwi_confounds>`. These are used to
estimate framewise displacement.  Additionally, measures of model fits
are saved for each slice for display in a carpet plot-like thing.


Head-motion estimation (TOPUP/eddy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:mod:`qsiprep.workflows.dwi.hmc.init_dwi_hmc_wf`

.. workflow::
    :graph2use: colored
    :simple_form: yes

    from qsiprep.workflows.dwi.hmc import init_dwi_hmc_wf
    wf = init_dwi_hmc_wf(hmc_transform="Affine",
                         hmc_model="eddy",
                         hmc_align_to="iterative",
                         mem_gb=3,
                         source_file='/path/to/dwi/sub-X_dwi.nii.gz',
                         omp_nthreads=1)

DTI and multi-shell HARDI can be passed to ``TOPUP`` and ``eddy`` for
head motion correction, susceptibility distortion correction and eddy current
correction. ``qsiprep`` will use the BIDS-specified fieldmaps to configure and
run ``TOPUP`` before passing the fieldmap to ``eddy`` if fieldmaps are available.

``eddy`` has many configuration options. Instead of making these commandline options,
you can specify them in a JSON file and pass that to ``qsiprep`` using the ``--eddy_config``
option. An example (default) eddy config json can be viewed or downloaded
`here <https://github.com/PennBBL/qsiprep/blob/master/qsiprep/data/eddy_params.json>`_

.. _dwi_ref:

DWI reference image estimation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:mod:`qsiprep.workflows.dwi.util.init_dwi_reference_wf`

.. workflow::
    :graph2use: orig
    :simple_form: yes

    from qsiprep.workflows.dwi.util import init_dwi_reference_wf
    wf = init_dwi_reference_wf(omp_nthreads=1)

This workflow estimates a reference image for a DWI series. This
procedure is different from the DWI reference image workflow in the
sense that true brain masking isn't usually done until later in the
pipeline for DWIs. It performs a generous automasking and uses
Dipy's histogram equalization on the b0 template generated during
motion correction.

Susceptibility Distortion Correction (SDC)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:mod:`qsiprep.workflows.fieldmap.base.init_sdc_wf`

.. figure:: _static/unwarping.svg
    :scale: 100%

    Applying susceptibility-derived distortion correction, based on
    fieldmap estimation.

The PEPOLAR and SyN-SDC workflows from FMRIPREP are copied here.
They operate on the output of reference estimation, after head
motion correction. For a complete list of possibilties here, see
:ref:`merging`.

.. _resampling:

Pre-processed DWIs in a different space
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:mod:`qsiprep.workflows.dwi.resampling.init_dwi_trans_wf`

.. workflow::
    :graph2use: orig
    :simple_form: yes

    from qsiprep.workflows.dwi.resampling import init_dwi_trans_wf
    wf = init_dwi_trans_wf(template="ACPC",
                           output_resolution=1.2,
                           use_fieldwarp=True,
                           use_compression=True,
                           to_mni=False,
                           write_local_bvecs=True,
                           mem_gb=3,
                           omp_nthreads=1)

A DWI series is resampled to an output space. The ``output_resolution`` is
specified on the commandline call. All transformations, including head motion
correction, susceptibility distortion correction, coregistration and (optionally)
normalization to the template is performed in a single shot using a Lanczos kernel.

There are two ways that the gradient vectors can be saved. This workflow always
produces a FSL-style bval/bvec pair for the image and a MRTrix .b gradient table
with the rotations from the linear transforms applied. You can also write out
a ``local_bvecs`` file that contains a 3d vector that has been rotated to account
for nonlinear transforms in each voxel. I'm not aware of any software that can
use these yet, but it's an interesting idea.


.. _b0_reg:

b0 to T1w registration
^^^^^^^^^^^^^^^^^^^^^^^^^

:mod:`qsiprep.workflows.dwi.registration.init_b0_to_anat_registration_wf`

.. workflow::
    :graph2use: orig
    :simple_form: yes

    from qsiprep.workflows.dwi.registration import init_b0_to_anat_registration_wf
    wf = init_b0_to_anat_registration_wf(
                                         mem_gb=3,
                                         omp_nthreads=1,
                                         transform_type="Rigid",
                                         write_report=False)

This just uses `antsRegistration`.



.. topic:: References

  .. [Power2016] Power JD, A simple but useful way to assess fMRI scan qualities.
     NeuroImage. 2016. doi: `10.1016/j.neuroimage.2016.08.009 <http://doi.org/10.1016/j.neuroimage.2016.08.009>`_
