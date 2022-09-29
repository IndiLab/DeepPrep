from pathlib import Path
from nipype import Node, Workflow, config, logging
from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from interface.freesurfer_interface import OrigAndRawavg, Brainmask, Filled, WhitePreaparc1, \
    InflatedSphere, JacobianAvgcurvCortparc, WhitePialThickness1, Curvstats, Cortribbon, \
    Parcstats, Pctsurfcon, Hyporelabel, Aseg7ToAseg, Aseg7, BalabelsMult, Segstats
from interface.fastsurfer_interface import Segment, Noccseg, N4BiasCorrect, TalairachAndNu, UpdateAseg, \
    SampleSegmentationToSurfave
from interface.fastcsr_interface import FastCSR
from interface.featreg_interface import FeatReg
from run import set_envrion
from multiprocessing import Pool
import threading
import os



# Part1 CPU
def init_structure_part1_wf(t1w_filess: list, subjects_dir: Path, subject_ids: list, ):
    # structure_part1_wf = Workflow(name=f'structure_part1_{subject_id.replace("-", "_")}_wf')
    structure_part1_wf = Workflow(name=f'structure_part1__wf')

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "subjects_dir",
            ]
        ),
        name="inputnode",
    )
    inputnode.inputs.subjects_dir = subjects_dir

    # orig_and_rawavg_node
    orig_and_rawavg_node = Node(OrigAndRawavg(), name='orig_and_rawavg_node')

    orig_and_rawavg_node.iterables = [('t1w_files', t1w_filess),
                                      ('subject_id', subject_ids)]
    orig_and_rawavg_node.synchronize = True
    # orig_and_rawavg_node.inputs.t1w_files = t1w_files
    # orig_and_rawavg_node.inputs.subjects_dir = subjects_dir
    # orig_and_rawavg_node.inputs.subject_id = subject_id
    orig_and_rawavg_node.inputs.threads = 8
    structure_part1_wf.connect([
        (inputnode, orig_and_rawavg_node, [("subjects_dir", "subjects_dir"),
                                           ]),
    ])
    return structure_part1_wf


set_envrion()
subjects_dir = Path("/mnt/ngshare/DeepPrep_flowtest/HNU_1_subwf")
os.environ['SUBJECTS_DIR'] = str(subjects_dir)

multi_subj_n_procs = 2

structure_part1_wf = init_structure_part1_wf(t1w_filess=[
    ["/mnt/ngshare/Data_Orig/HNU_1/sub-0025427/ses-01/anat/sub-0025427_ses-01_T1w.nii.gz"],
    ["/mnt/ngshare/Data_Orig/HNU_1/sub-0025428/ses-01/anat/sub-0025428_ses-01_T1w.nii.gz"]],
    subjects_dir=subjects_dir,
    subject_ids=['sub-0025427', 'sub-0025428'])
structure_part1_wf.base_dir = subjects_dir
# structure_part1_wf_res = structure_part1_wf.run('MultiProc', plugin_args={'n_procs': multi_subj_n_procs})
# print()
# exit()


# Part2 GPU
def init_structure_part2_wf(subjects_dir: Path, subject_ids: list,
                            python_interpret: Path,
                            fastsurfer_home: Path):
    structure_part2_wf = Workflow(name=f'structure_part2__wf')

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "subjects_dir",
            ]
        ),
        name="inputnode",
    )
    inputnode.inputs.subjects_dir = subjects_dir

    # segment_node
    fastsurfer_eval = fastsurfer_home / 'FastSurferCNN' / 'eval.py'  # inference script
    weight_dir = fastsurfer_home / 'checkpoints'  # model checkpoints dir
    network_sagittal_path = weight_dir / "Sagittal_Weights_FastSurferCNN" / "ckpts" / "Epoch_30_training_state.pkl"
    network_coronal_path = weight_dir / "Coronal_Weights_FastSurferCNN" / "ckpts" / "Epoch_30_training_state.pkl"
    network_axial_path = weight_dir / "Axial_Weights_FastSurferCNN" / "ckpts" / "Epoch_30_training_state.pkl"

    segment_node = Node(Segment(), f'segment_node')
    segment_node.iterables = [("subject_id", subject_ids)]
    segment_node.synchronize = True

    segment_node.inputs.python_interpret = python_interpret
    segment_node.inputs.eval_py = fastsurfer_eval
    segment_node.inputs.network_sagittal_path = network_sagittal_path
    segment_node.inputs.network_coronal_path = network_coronal_path
    segment_node.inputs.network_axial_path = network_axial_path

    structure_part2_wf.connect([
        (inputnode, segment_node, [("subjects_dir", "subjects_dir"),
                                   ]),
    ])
    return structure_part2_wf


set_envrion()
subjects_dir = Path("/mnt/ngshare/DeepPrep_flowtest/HNU_1_subwf")
os.environ['SUBJECTS_DIR'] = str(subjects_dir)
python_interpret = Path('/home/youjia/anaconda3/envs/3.8/bin/python3')
pwd = Path.cwd()
fastsurfer_home = pwd / "FastSurfer"

multi_subj_n_procs = 2

structure_part2_wf = init_structure_part2_wf(subjects_dir=subjects_dir,
                                             subject_ids=['sub-0025427', 'sub-0025428'],
                                             python_interpret=python_interpret,
                                             fastsurfer_home=fastsurfer_home)
structure_part2_wf.base_dir = subjects_dir
# structure_part2_wf.run('MultiProc', plugin_args={'n_procs': multi_subj_n_procs})
# print()
# exit()


# Part3 CPU
def init_structure_part3_wf(subjects_dir: Path, subject_ids: list,
                            python_interpret: Path,
                            fastsurfer_home: Path,
                            freesurfer_home: Path):

    structure_part3_wf = Workflow(name=f'structure_part3__wf')

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "subjects_dir",
            ]
        ),
        name="inputnode",
    )
    inputnode.inputs.subjects_dir = subjects_dir

    # auto_noccseg_node
    fastsurfer_reduce_to_aseg_py = fastsurfer_home / 'recon_surf' / 'reduce_to_aseg.py'  # inference script

    auto_noccseg_node = Node(Noccseg(), name='auto_noccseg_node')
    auto_noccseg_node.iterables = [("subject_id", subject_ids)]
    auto_noccseg_node.synchronize = True
    auto_noccseg_node.inputs.python_interpret = python_interpret
    auto_noccseg_node.inputs.reduce_to_aseg_py = fastsurfer_reduce_to_aseg_py

    # auto_noccseg_node.inputs.mask_file = subjects_dir / subject_id / 'mri' / 'mask.mgz'
    # auto_noccseg_node.inputs.aseg_noCCseg_file = subjects_dir / subject_id / 'mri' / 'aseg.auto_noCCseg.mgz'

    # N4_bias_correct_node
    correct_py = fastsurfer_home / "recon_surf" / "N4_bias_correct.py"

    N4_bias_correct_node = Node(N4BiasCorrect(), name="N4_bias_correct_node")
    N4_bias_correct_node.inputs.subjects_dir = subjects_dir
    N4_bias_correct_node.inputs.threads = 8
    N4_bias_correct_node.inputs.python_interpret = python_interpret
    N4_bias_correct_node.inputs.correct_py = correct_py
    # N4_bias_correct_node.inputs.orig_nu_file = subjects_dir / subject_id / "mri" / "orig_nu.mgz"

    # TalairachAndNu
    talairach_and_nu_node = Node(TalairachAndNu(), name="talairach_and_nu_node")
    talairach_and_nu_node.inputs.subjects_dir = subjects_dir
    # talairach_and_nu_node.inputs.subject_id = subject_id
    talairach_and_nu_node.inputs.threads = 8

    talairach_and_nu_node.inputs.mni305 = freesurfer_home / "average" / "mni305.cor.mgz"  # atlas

    # talairach_and_nu_node.inputs.talairach_lta = subjects_dir / subject_id / 'mri' / 'transforms' / 'talairach.lta'
    # talairach_and_nu_node.inputs.nu_file = subjects_dir / subject_id / 'mri' / 'nu.mgz'

    # Brainmask
    brainmask_node = Node(Brainmask(), name='brainmask_node')
    brainmask_node.inputs.subjects_dir = subjects_dir
    # brainmask_node.inputs.subject_id = subject_id
    brainmask_node.inputs.need_t1 = True

    # brainmask_node.inputs.T1_file = subjects_dir / subject_id / 'mri' / 'T1.mgz'
    # brainmask_node.inputs.brainmask_file = subjects_dir / subject_id / 'mri' / 'brainmask.mgz'
    # brainmask_node.inputs.norm_file = subjects_dir / subject_id / 'mri' / 'norm.mgz'

    # UpdateAseg
    updateaseg_node = Node(UpdateAseg(), name='updateaseg_node')
    updateaseg_node.inputs.subjects_dir = subjects_dir
    # updateaseg_node.inputs.subject_id = subject_id
    updateaseg_node.inputs.paint_cc_file = fastsurfer_home / 'recon_surf' / 'paint_cc_into_pred.py'
    updateaseg_node.inputs.python_interpret = python_interpret

    # updateaseg_node.inputs.aseg_auto_file = subjects_dir / subject_id / 'mri' / 'aseg.auto.mgz'
    # updateaseg_node.inputs.cc_up_file = subjects_dir / subject_id / 'mri' / 'transforms' / 'cc_up.lta'
    # updateaseg_node.inputs.aparc_aseg_file = subjects_dir / subject_id / 'mri' / 'aparc.DKTatlas+aseg.deep.withCC.mgz'

    # Filled
    filled_node = Node(Filled(), name='filled_node')
    filled_node.inputs.subjects_dir = subjects_dir
    # filled_node.inputs.subject_id = subject_id
    filled_node.inputs.threads = 8

    structure_part3_wf.connect([
        (inputnode, auto_noccseg_node, [("subjects_dir", "subjects_dir"),
                                        ]),
        (auto_noccseg_node, N4_bias_correct_node, [("orig_file", "orig_file"),
                                                   ("mask_file", "mask_file"),
                                                   ("subject_id", "subject_id"),
                                                      ]),
        (auto_noccseg_node, talairach_and_nu_node, [("orig_file", "orig_file"), ("subject_id", "subject_id"),
                                                       ]),
        (N4_bias_correct_node, talairach_and_nu_node, [("orig_nu_file", "orig_nu_file"),
                                                       ]),
        (talairach_and_nu_node, brainmask_node, [("nu_file", "nu_file"), ("subject_id", "subject_id"),
                                                 ]),
        (auto_noccseg_node, brainmask_node, [("mask_file", "mask_file")
                                             ]),
        (brainmask_node, updateaseg_node, [("norm_file", "norm_file"), ("subject_id", "subject_id"),
                                           ]),
        (auto_noccseg_node, updateaseg_node, [("aparc_DKTatlas_aseg_deep", "seg_file"),
                                              ("aseg_noCCseg_file", "aseg_noCCseg_file"),
                                         ]),
        (updateaseg_node, filled_node, [("aseg_auto_file", "aseg_auto_file"), ("subject_id", "subject_id"),
                                        ]),
        (brainmask_node, filled_node, [("brainmask_file", "brainmask_file"), ("norm_file", "norm_file"),
                                       ]),
        (talairach_and_nu_node, filled_node, [("talairach_lta", "talairach_lta"),
                                              ]),
    ])
    return structure_part3_wf


set_envrion()
subjects_dir = Path("/mnt/ngshare/DeepPrep_flowtest/HNU_1_subwf")
os.environ['SUBJECTS_DIR'] = str(subjects_dir)
python_interpret = Path('/home/youjia/anaconda3/envs/3.8/bin/python3')
pwd = Path.cwd()
fastsurfer_home = pwd / "FastSurfer"
freesurfer_home = Path('/usr/local/freesurfer')

multi_subj_n_procs = 2

structure_part3_wf = init_structure_part3_wf(subjects_dir=subjects_dir,
                                             subject_ids=['sub-0025427', 'sub-0025428'],
                                             python_interpret=python_interpret,
                                             fastsurfer_home=fastsurfer_home,
                                             freesurfer_home=freesurfer_home)
structure_part3_wf.base_dir = subjects_dir
# structure_part3_wf.run('MultiProc', plugin_args={'n_procs': multi_subj_n_procs})
# print()
# exit()


def init_structure_part4_wf(subjects_dir: Path, subject_ids: list,
                            python_interpret: Path,
                            fastcsr_home: Path):
    structure_part4_wf = Workflow(name=f'structure_part4__wf')

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "subjects_dir",
            ]
        ),
        name="inputnode",
    )
    inputnode.inputs.subjects_dir = subjects_dir
    # FastCSR
    fastcsr_node = Node(FastCSR(), name="fastcsr_node")
    fastcsr_node.inputs.subjects_dir = subjects_dir
    fastcsr_node.iterables = [("subject_id", subject_ids)]
    fastcsr_node.synchronize = True

    fastcsr_node.inputs.python_interpret = python_interpret
    fastcsr_node.inputs.fastcsr_py = fastcsr_home / 'pipeline.py'

    structure_part4_wf.connect([
        (inputnode, fastcsr_node, [("subjects_dir", "subjects_dir"),
                                   ]),
    ])
    return structure_part4_wf


set_envrion()
subjects_dir = Path("/mnt/ngshare/DeepPrep_flowtest/HNU_1_subwf")
os.environ['SUBJECTS_DIR'] = str(subjects_dir)
python_interpret = Path('/home/youjia/anaconda3/envs/3.8/bin/python3')
pwd = Path.cwd()
fastcsr_home = pwd / "FastCSR"

multi_subj_n_procs = 2

structure_part4_wf = init_structure_part4_wf(subjects_dir=subjects_dir,
                                             subject_ids=['sub-0025427', 'sub-0025428'],
                                             python_interpret=python_interpret,
                                             fastcsr_home=fastcsr_home)
structure_part4_wf.base_dir = str(subjects_dir)
structure_part4_wf.run('MultiProc', plugin_args={'n_procs': multi_subj_n_procs})
print()
exit()


def pipeline(t1w_files, subjects_dir, subject_id):
    pwd = Path.cwd()
    python_interpret = Path('/home/youjia/anaconda3/envs/3.8/bin/python3')
    fastsurfer_home = pwd / "FastSurfer"
    freesurfer_home = Path('/usr/local/freesurfer')
    fastcsr_home = pwd.parent / "deepprep_pipeline/FastCSR"
    featreg_home = pwd.parent / "deepprep_pipeline/FeatReg"

    # subjects_dir = Path('/mnt/ngshare/DeepPrep_flowtest/V001/derivatives/deepprep/Recon')
    # subject_id = 'sub-001'

    os.environ['SUBJECTS_DIR'] = str(subjects_dir)

    wf = init_single_structure_wf(t1w_files, subjects_dir, subject_id, python_interpret, fastsurfer_home,
                                  freesurfer_home, fastcsr_home, featreg_home)
    wf.base_dir = subjects_dir
    # wf.write_graph(graph2use='flat', simple_form=False)
    config.update_config({'logging': {'log_directory': os.getcwd(),
                                      'log_to_file': True}})
    logging.update_logging(config)
    wf.run()

    ##############################################################
    # t1w_files = [
    #     f'/mnt/ngshare/Data_Mirror/SDCFlows_test/MSC1/sub-MSC01/ses-struct01/anat/sub-MSC01_ses-struct01_run-01_T1w.nii.gz',
    # ]
    # t1w_files = ['/home/anning/Downloads/anat/001/guo_mei_hui_fMRI_22-9-20_ABI1_t1iso_TFE_20220920161141_201.nii.gz']
    pwd = Path.cwd()
    python_interpret = Path('/home/anning/miniconda3/envs/3.8/bin/python3')
    fastsurfer_home = pwd / "FastSurfer"
    freesurfer_home = Path('/usr/local/freesurfer')
    fastcsr_home = pwd.parent / "deepprep_pipeline/FastCSR"
    featreg_home = pwd.parent / "deepprep_pipeline/FeatReg"

    # subjects_dir = Path('/mnt/ngshare/Data_Mirror/pipeline_test')
    # subject_id = 'sub-guomeihui'
    #
    os.environ['SUBJECTS_DIR'] = str(subjects_dir)
    #
    wf = init_single_structure_wf(t1w_files, subjects_dir, subject_id, python_interpret, fastsurfer_home,
                                  freesurfer_home, fastcsr_home, featreg_home)
    wf.base_dir = f'/mnt/ngshare/Data_Mirror/pipeline_test'
    wf.write_graph(graph2use='flat', simple_form=False)
    wf.run()


class myThread(threading.Thread):  # 继承父类threading.Thread
    def __init__(self, t1w_files, subjects_dir, subject_id):
        threading.Thread.__init__(self)
        self.t1w_files = t1w_files
        self.subjects_dir = subjects_dir
        self.subject_id = subject_id

    def run(self):  # 把要执行的代码写到run函数里面 线程在创建后会直接运行run函数
        pipeline(self.t1w_files, self.subjects_dir, self.subject_id)


if __name__ == '__main__':
    import os
    import bids

    set_envrion()

    data_path = Path("/run/user/1000/gvfs/sftp:host=30.30.30.66,user=zhenyu/mnt/ngshare/Data_Orig/HNU_1")
    layout = bids.BIDSLayout(str(data_path), derivatives=False)
    subjects_dir = Path("/mnt/ngshare/DeepPrep_flowtest/HNU_1")
    os.environ['SUBJECTS_DIR'] = "/mnt/ngshare/DeepPrep_flowtest/HNU_1"

    Multi_num = 3

    thread_list = []

    for t1w_file in layout.get(return_type='filename', suffix="T1w"):
        sub_info = layout.parse_file_entities(t1w_file)
        subject_id = f"sub-{sub_info['subject']}-ses-{sub_info['session']}"
        # print(subject_id)

        thread_list.append(myThread([t1w_file], subjects_dir, subject_id))
        # pipeline(t1w, subjects_dir, subject_id)

    thread_list = thread_list[200:]
    i = 0
    while i < len(thread_list):
        if i > len(thread_list) - Multi_num:
            for thread in thread_list[i:]:
                thread.start()
            for thread in thread_list[i:]:
                thread.join()
            i = len(thread_list)
        else:
            for thread in thread_list[i:i + Multi_num]:
                thread.start()
            for thread in thread_list[i:i + Multi_num]:
                thread.join()
            i += Multi_num
            print()
