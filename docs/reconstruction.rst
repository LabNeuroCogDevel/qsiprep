.. include:: links.rst

.. _reconstruction:


Reconstruction
==============

You can send the outputs from ``qsiprep`` to other software packages
by specifying a JSON file with the ``--recon-spec`` option. Here we use
"reconstruction" to mean reconstructing ODFs/FODs/EAPs and connectivity matrices
from the preprocessed diffusion data.

The easiest way to get started is to use one of the :ref:`preconfigured_workflows`.
Instead of specifying a path to a file you can choose from the following:

+-------------------------------+--------------+-------------+---------+-----------------+----------------+
| Option                        | Requires SDC | MultiShell  |   DSI   | DTI             |  Tractography  |
+===============================+==============+=============+=========+=================+================+
|:ref:`mrtrix_msmt_csd`         |    Yes       |  Required   |    No   |      No         | Probabilistic  |
+-------------------------------+--------------+-------------+---------+-----------------+----------------+
|:ref:`mrtrix_dhollander`       |    Yes       |    Yes      |    No   |     Yes         | Probabilistic  |
+-------------------------------+--------------+-------------+---------+-----------------+----------------+
|:ref:`mrtrix_dhollander_no5tt` |     No       |    Yes      |    No   |     Yes         | Probabilistic  |
+-------------------------------+--------------+-------------+---------+-----------------+----------------+
|:ref:`mrtrix_tckglobal`        |    Yes       |   Required  |    No   |      No         |    Global      |
+-------------------------------+--------------+-------------+---------+-----------------+----------------+
|:ref:`dsi_studio_gqi`          | Recommended  |    Yes      |   Yes   |    Yes*         | Deterministic  |
+-------------------------------+--------------+-------------+---------+-----------------+----------------+
|:ref:`dipy_mapmri`             | Recommended  |    Yes      |   Yes   |      No         |   Both         |
+-------------------------------+--------------+-------------+---------+-----------------+----------------+
|:ref:`dipy_3dshore`            | Recommended  |    Yes      |   Yes   |      No         |   Both         |
+-------------------------------+--------------+-------------+---------+-----------------+----------------+
|:ref:`csdsi_3dshore`           | Recommended  |    Yes      |   Yes   |      No         |   Both         |
+-------------------------------+--------------+-------------+---------+-----------------+----------------+

\* Not recommended

These workflows each take considerable processing time, because they output as many versions of
connectivity as possible. All :ref:`connectivity_atlases`  and all possible weightings are
included. Each workflow corresponds to a JSON file that can be found in QSIprep's
`github <https://github.com/PennBBL/qsiprep/tree/master/qsiprep/data/pipelines>`_. For extra
information about how to customize these, see :ref:`custom_reconstruction`.

To use a pre-packaged workflow, simply provide the name from the leftmost column above for the
``--recon-spec`` argument. For example::

  $ qsiprep-docker \
      --bids_dir /path/to/bids \
      --recon_input /output/from/qsiprep \
      --recon_spec mrtrix_msmt_csd \
      --output_dir /where/my/reconstructed/data/goes \
      --analysis_level participant \
      --fs-license-file /path/to/license.txt


``qsiprep`` supports a limited number of algorithms that are wrapped in
nipype workflows and can be configured and connected based on the
recon spec JSON file.  The output from one workflow can be the input to
another as long as the output from the upstream workflow matches the inputs to
the downstream workflow. The :ref:`recon_workflows` section lists all the
available workflows and their inputs and outputs.


.. _connectivity:

Reconstruction Outputs: Connectivity matrices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Instead of offering a bewildering number of options for constructing connectivity matrices,
``qsiprep`` will construct as many connectivity matrices as it can given the reconstruction
methods. It is **highly** recommended that you pick a weighting scheme before you run
these pipelines and only look at those numbers. If you look at more than one weighting method
be sure to adjust your statistics for the additional comparisons.

.. _connectivity_atlases:

Atlases
^^^^^^^

The following atlases are included in ``qsiprep`` and are used by default in the
:ref:`preconfigured_workflows`. If you use one of them please be sure to cite
the relevant publication.

 * ``schaefer100x7``, ``schaefer100x17``, ``schaefer200x7``, ``schaefer200x17``,
   ``schaefer400x7``, ``schaefer400x17``: [Schaefer2017]_, [Yeo2011]_
 * ``brainnetome246``: [Fan2016]_
 * ``aicha384``: [Joliot2015]_
 * ``gordon333``: [Gordon2014]_
 * ``aal116``: [TzourioMazoyer2002]_
 * ``power264``: [Power2011]_

.. _custom_atlases:

Using custom atlases
^^^^^^^^^^^^^^^^^^^^

It's possible to use your own atlases provided you can match the format ``qsiprep`` uses to
read atlases. The ``qsiprep`` atlas set can be downloaded directly from
`box  <https://upenn.box.com/shared/static/8k17yt2rfeqm3emzol5sa0j9fh3dhs0i.xz>`_.

In this directory there must exist a JSON file called ``atlas_config.json`` containing an
entry for each atlas you would like included. The format is::

  {
    "my_custom_atlas": {
      "file": "file_in_this_directory.nii.gz",
      "node_names": ["Region1_L", "Region1_R" ... "RegionN_R"],
      "node_ids": [1, 2, ..., N]
    }
    ...
  }

Where ``"node_names"`` are the text names of the regions in ``"my_custom_atlas"`` and
``"node_ids"`` are the numbers in the nifti file that correspond to each region. When
:ref:`custom_reconstruction` you can then inclued ``"my_custom_atlas"`` in the ``"atlases":[]``
section.

The directory containing ``atlas_config.json`` and the atlas nifti files should be mounted in
the container at ``/atlas/qsirecon_atlases``. If using ``qsiprep-docker`` or
``qsiprep-singularity`` this can be done with ``--custom-atlases /path/to/my/atlases`` or
if you're running on your own system (not recommended) you can set the environment variable
``QSIRECON_ATLAS=/path/to/my/atlases``.

The nifti images should be registered to the
`MNI152NLin2009cAsym <https://github.com/PennBBL/qsiprep/blob/master/qsiprep/data/mni_1mm_t1w_lps.nii.gz>`_
included in ``qsiprep``.
It is essential that your images are in the LPS+ orientation and have the sform zeroed-out
in the header. **Be sure to check for alignment and orientation** in your outputs.



.. _preconfigured_workflows:

Pre-configured recon_workflows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _mrtrix_msmt_csd:

``mrtrix_msmt_csd``
^^^^^^^^^^^^^^^^^^^

This workflow explicitly uses the T1w-based segmentation to estimate response functions for
white matter, gray matter and CSF. Tissue-specific response functions are estimated using the
T1w-based FAST segmentation. Good alignment between the dMRI and T1w scan is therefore required:
susceptibility distortion correction must have been performed during preprocessing. Additionally,
a unique shell is required for each tissue response function. This means that at least 3 b>0
shells need to be included in the preprocessed data.

The output from ``qsiprep`` is sent to  `dwi2response (msmt_5tt)`_ [Jeurissen2014]_ with a mask
based on the T1w. The GM, WM and CSF FODs, along with the anatomical segmentation are input to
tckgen_, which uses the iFOD2 probabilistic tracking method to generate 1e7 streamlines with a
maximum length of 250mm, minimum length of 30mm, FOD power of 0.33, cropping performed at the
GM/WM interface, and backtracking. Weights for each streamline were calculated using SIFT2_
[Smith2015]_ and were included for while estimating the structural connectivity matrix.


.. _mrtrix_dhollander:

``mrtrix_dhollander``
^^^^^^^^^^^^^^^^^^^^^

Unlike :ref:`mrtrix_msmt_csd`, this workflow uses an unsupervised learning approach to
estimate response functions for white matter, gray matter and CSF [Dhollander2016]_, [Dhollander2018]_.
A unique shell is required for each tissue response function. This means that at least 3 b>0
shells need to be included in the preprocessed data.

The output from ``qsiprep`` is sent to  `dwi2response (dhollander)`_ [Dhollander2016]_ with a mask
based on the T1w. The GM, WM and CSF FODs along with the FAST segmentation are input to
tckgen_, which uses the iFOD2 probabilistic tracking method to generate 1e7 streamlines with a
maximum length of 250mm, minimum length of 30mm, FOD power of 0.33, cropping performed at the
GM/WM interface, and backtracking. Weights for each streamline were calculated using SIFT2_
[Smith2015]_ and were included for while estimating the structural connectivity matrix.

Although the T1w-based tissue segmentation is *not* used for the tissue-specific response
functions, it *is* used for Anatomically constrained tractography by tckgen_. Therefore
distortion correction is still required for this workflow. A workflow that does not hinge on
distortion-correction data is :ref:`mrtrix_dhollander_no5tt`.



.. _mrtrix_dhollander_no5tt:

``mrtrix_dhollander_no5tt``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

This pipeline is nearly identical to :ref:`mrtrix_dhollander` except that Anatomically Constrained
Tractography is disabled in tckgen_. Not using any distortion correction is a bad idea, but
if that is your choice, you can use this pipeline and get connectivity matrices. Interpret their
contents at your own peril.


.. _mrtrix_tckglobal:

``mrtrix_tckglobal``
^^^^^^^^^^^^^^^^^^^^

MRtrix has a multi-shell multi-tissue version of Global tractography [Christiaens2015]_. This
pipeline uses segmentation-based multi-tissue response function estimation
(like :ref:`mrtrix_msmt_csd`). The FODs and streamlines are then created inside tckglobal_.
The ultimate number of streamlines is dependent on the input data.


.. _dsi_studio_gqi:

``dsi_studio_gqi``
^^^^^^^^^^^^^^^^^^

Here the standard GQI plus deterministic tractography pipeline is used [Yeh2013]_.  GQI works on
almost any imaginable sampling scheme because DSI Studio will internally interpolate the q-space
data so  symmetry requirements are met. GQI models the water diffusion ODF, so ODF peaks are much
smaller  than you see with CSD. This results in a rather conservative peak detection, which greatly
benefits from having more diffusion data than a typical DTI.

5 million streamlines are created with a maximum length of 250mm, minimum length of 30mm,
random seeding, a step size of 1mm and an automatically calculated QA threshold.

Additionally, a number of anisotropy scalar images are produced such as QA, GFA and ISO.

.. _dipy_mapmri:

``dipy_mapmri``
^^^^^^^^^^^^^^^

The MAPMRI method is used to estimate EAPs from which ODFs are calculated analytically. This
method produces scalars like RTOP, RTAP, QIV, MSD, etc.

The ODFs are saved in DSI Studio format and tractography is run identically to that in
:ref:`dsi_studio_gqi`.


.. _dipy_3dshore:

``dipy_3dshore``
^^^^^^^^^^^^^^^^

This uses the BrainSuite 3dSHORE basis in a Dipy reconstruction. Much like :ref:`dipy_mapmri`,
a slew of anisotropy scalars are estimated. Here the :ref:`dsi_studio_gqi` fiber tracking is
again run on the 3dSHORE-estimated ODFs.

.. _csdsi_3dshore:

``csdsi_3dshore``
^^^^^^^^^^^^^^^^^

**[EXPERIMENTAL]** This pipeline is for DSI or compressed-sensing DSI. The first step is a
L2-regularized 3dSHORE reconstruction of the ensemble average propagator in each voxel. These EAPs
are then used for two purposes

 1. To calculate ODFs, which are then sent to DSI Studio for tractography
 2. To estimate signal for a multishell (specifically HCP) sampling scheme, which is run
    through the :ref:`mrtrix_msmt_csd` pipeline

All outputs, including the imputed HCP sequence are saved in the outputs directory.

.. _custom_reconstruction:

Building a custom reconstruction pipeline
==========================================


Instead of going through each possible element of a pipeline, we will go through
a simple example and describe its components.

Simple DSI Studio example
~~~~~~~~~~~~~~~~~~~~~~~~~~

The reconstruction pipeline is created by the user and specified in a JSON
file similar to the following::

  {
    "name": "dsistudio_pipeline",
    "space": "T1w",
    "anatomical": ["mrtrix_5tt"],
    "atlases": ["schaefer100x7", "schaefer100x17", "schaefer200x7", "schaefer200x7", "schaefer400x7", "schaefer400x17", "brainnetome246", "aicha384", "gordon333", "aal116", "power264"],
    "nodes": [
      {
        "name": "dsistudio_gqi",
        "software": "DSI Studio",
        "action": "reconstruction",
        "input": "qsiprep",
        "output_suffix": "gqi",
        "parameters": {"method": "gqi"}
      },
      {
        "name": "scalar_export",
        "software": "DSI Studio",
        "action": "export",
        "input": "dsistudio_gqi",
        "output_suffix": "gqiscalar"
      }
    ]
  }

Pipeline level metadata
^^^^^^^^^^^^^^^^^^^^^^^^^

The ``"name"`` element defines the name of the pipeline. This will ultimately
be the name of the output directory. By setting ``"space": "T1w"`` we specify
that all operations will take place in subject anatomical (``"T1w"``) space.
Many "connectomics" algorithms require a brain parcellation. A number of these
come packaged with ``qsiprep`` in the Docker image. In this case, the
atlases will be transformed from group template space to subject anatomical space
because we specified  ``"space": "T1w"`` earlier. Be sure a warp is calculated if
using these (transforms_).

Pipeline nodes
^^^^^^^^^^^^^^^

The ``"nodes"`` list contains the workflows that will be run as a part of the
reconstruction pipeline. All nodes must have a ``name`` element, this serves
as an id for this node and is used to connect its outputs to a downstream
node. In this example we can see that the node with ``"name": "dsistudio_gqi"``
sends its outputs to the node with ``"name": "scalar_export"`` because
the ``"name": "scalar_export"`` node specifies ``"input": "dsistudio_gqi"``.
If no ``"input"`` is specified for a node, it is assumed that the
outputs from ``qsiprep`` will be its inputs.

By specifying ``"software": "DSI Studio"`` we will be using algorithms implemented
in `DSI Studio`_. Other options include MRTrix_ and Dipy_. Since there are many
things that `DSI Studio`_ can do, we specify that we want to reconstruct the
output from ``qsiprep`` by adding ``"action": "reconstruction"``. Additional
parameters can be sent to specify how the reconstruction should take place in
the ``"parameters"`` item. Possible options for ``"software"``, ``"action"``
and ``"parameters"`` can be found in the :ref:`recon_workflows` section.

You will have access to all the intermediate data in the pipeline's working directory,
but can specify which outputs you want to save to the output directory by setting
an ``"output_suffix"``. Looking at the outputs for a workflow in the :ref:`recon_workflows`
section you can see what is produced by each workflow. Each of these files
will be saved in your output directory for each subject with a name matching
your specified ``"output_suffix"``. In this case it will produce a file
``something_space-T1w_gqi.fib.gz``.  Since a fib file is produced by this node
and the downstream ``export_scalars`` node uses it, the scalars produced from
that node will be from this same fib file.

Executing the reconstruction pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Assuming this file is called ``qgi_scalar_export.json`` and you've installed
``qsiprep-container`` you can execute this pipeline with::

  $ qsiprep-docker \
      --bids_dir /path/to/bids \
      --recon_input /output/from/qsiprep \
      --recon_spec gqi_scalar_export.json \
      --output_dir /where/my/reconstructed/data/goes \
      --analysis_level participant \
      --fs-license-file /path/to/license.txt


.. _transforms:

Spaces and transforms
^^^^^^^^^^^^^^^^^^^^^^^

Transforming the a reconstruction output to template space requires that the
spatial normalization transform is calculated. This can be accomplished in
two ways

  1. During preprocessing you included ``--output-spaces template``. This will also
     result in your preprocessed DWI series being written in template space, which
     you likely don't want.
  2. You include the ``--force-spatial-normalization`` argument during preprocessing.
     This will create the warp to your template and store it in the derivatives directory
     but will not write your preprocessed DWI series in template space.

Some of the workflows require a warp to a template. For example, connectivity_ will use
this warp to transform atlases into T1w space for calculating a connectivity matrix.
