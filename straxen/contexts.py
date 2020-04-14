import warnings

from immutabledict import immutabledict
import strax
import straxen


common_opts = dict(
    register_all=[
        straxen.pulse_processing,
        straxen.peaklet_processing,
        straxen.peak_processing,
        straxen.event_processing,
        straxen.double_scatter,
        straxen.nveto_recorder,
        straxen.nveto_pulse_processing],
    store_run_fields=(
        'name', 'number',
        'reader.ini.name', 'tags.name',
        'start', 'end', 'livetime',
        'trigger.events_built'),
    check_available=('raw_records', 'records', 'peaklets',
                     'events', 'event_info'))


x1t_common_config = dict(
    check_raw_record_overlaps=False,
    n_tpc_pmts=248,
    channel_map=immutabledict(
        # (Minimum channel, maximum channel)
        tpc=(0, 247),
        diagnostic=(248, 253),
        aqmon=(254, 999)),
    hev_gain_model=('to_pe_per_run',
                    'https://raw.githubusercontent.com/XENONnT/strax_auxiliary_files/master/to_pe.npy'),
    gain_model=('to_pe_per_run',
                'https://raw.githubusercontent.com/XENONnT/strax_auxiliary_files/master/to_pe.npy'),
    pmt_pulse_filter=(
        0.012, -0.119,
        2.435, -1.271, 0.357, -0.174, -0., -0.036,
        -0.028, -0.019, -0.025, -0.013, -0.03, -0.039,
        -0.005, -0.019, -0.012, -0.015, -0.029, 0.024,
        -0.007, 0.007, -0.001, 0.005, -0.002, 0.004, -0.002),
    tail_veto_threshold=int(1e5),
    save_outside_hits=(3, 3),
    hit_min_amplitude=straxen.adc_thresholds(),
    # Some setting which are required by the fake daq for the nVETO HdM test set-up but not needed otherwise:
    # n_nveto_pmts=32, <-- commented this line out in order to not to cause warning massages.
)

xnt_common_config = dict(
    n_tpc_pmts=494,
    n_nveto_pmts=120,
    gain_model=('to_pe_constant',
                0.005),
#    gain_model_nveto=('to_pe_constant',  #otherwise we get all the time warnings...
#                      0.005),
    channel_map=immutabledict(
         # (Minimum channel, maximum channel)
         # Channels must be listed in a ascending order!
         tpc=(0, 493),
         he=(500, 752),  # high energy
         aqmon=(790, 807),
         aqmonnv=(808, 815),  # nveto acquisition monitor
         tpc_blank=(999, 999),
         mv=(1000, 1083),
         mv_blank=(1999, 1999), 
         nveto=(2000, 2119),
         nveto_blank=(2999, 2999),
    )
)


##
# XENONnT
##


def xenonnt_online(output_folder='./strax_data',
                   we_are_the_daq=False,
                   **kwargs):
    """XENONnT online processing and analysis"""
    context_options = {
        **straxen.contexts.common_opts,
        **kwargs}

    st = strax.Context(
        storage=[
            straxen.RunDB(
                readonly=not we_are_the_daq,
                runid_field='number',
                new_data_path=output_folder),
        ],
        config=straxen.contexts.xnt_common_config,
        **context_options)
    st.register([straxen.DAQReader, straxen.LEDCalibration])

    if not we_are_the_daq:
        st.storage += [
            strax.DataDirectory(
                '/dali/lgrandi/xenonnt/raw',
                readonly=True,
                take_only='raw_records'),
            strax.DataDirectory(
                '/dali/lgrandi/xenonnt/processed',
                readonly=True)]
        if output_folder:
            st.storage.append(
                strax.DataDirectory(output_folder))

        st.context_config['forbid_creation_of'] = 'raw_records'

    st.context_config['check_available'] = ('raw_records',)

    return st


def xenonnt_led(**kwargs):
    st = xenonnt_online(**kwargs)
    st.context_config['check_available'] = ('raw_records', 'led_calibration')
    # Return a new context with only raw_records and led_calibration registered
    return st.new_context(
        replace=True,
        register=[straxen.DAQReader, straxen.LEDCalibration],
        config=st.config,
        storage=st.storage,
        **st.context_config)


def nt_simulation():
    import wfsim
    return strax.Context(
        storage='./strax_data',
        register=wfsim.RawRecordsFromFax,
        config=dict(
            nchunk=1,
            event_rate=1,
            chunk_size=10,
            detector='XENONnT',
            fax_config='https://raw.githubusercontent.com/XENONnT/'
                       'strax_auxiliary_files/master/fax_files/fax_config_nt.json',
            **xnt_common_config),
        **straxen.contexts.common_opts)


##
# XENON1T
##

def demo():
    """Return strax context used in the straxen demo notebook"""
    straxen.download_test_data()
    return strax.Context(
            storage=[strax.DataDirectory('./strax_data'),
                     strax.DataDirectory('./strax_test_data', readonly=True)],
            register=straxen.RecordsFromPax,
            free_options=('channel_map',),
            forbid_creation_of=('raw_records',),
            config=dict(**x1t_common_config),
            **common_opts)


def fake_daq():
    """Context for processing fake DAQ data in the current directory"""
    return strax.Context(
        storage=[strax.DataDirectory('./strax_data',
                                     provide_run_metadata=False),
                 # Fake DAQ puts run doc JSON in same folder:
                 strax.DataDirectory('./from_fake_daq',
                                     readonly=True)],
        config=dict(daq_input_dir='./from_fake_daq',
                    daq_chunk_duration=int(2e9),
                    daq_compressor='lz4',
                    n_readout_threads=8,
                    daq_overlap_chunk_duration=int(2e8),
                    **x1t_common_config),
        register=straxen.Fake1TDAQReader,
        **common_opts)


def xenon1t_dali(output_folder='./strax_data', build_lowlevel=False):
    return strax.Context(
        storage=[
            strax.DataDirectory(
                '/dali/lgrandi/xenon1t/strax_converted/raw',
                take_only='raw_records',
                provide_run_metadata=True,
                deep_scan=False,
                readonly=True),
            strax.DataDirectory(
                '/dali/lgrandi/xenon1t/strax_converted/processed',
                readonly=True,
                provide_run_metadata=False),
            strax.DataDirectory(output_folder,
                                provide_run_metadata=False)],
        register=straxen.RecordsFromPax,
        free_options=('channel_map',),
        config=dict(**x1t_common_config),
        # When asking for runs that don't exist, throw an error rather than
        # starting the pax converter
        forbid_creation_of=(
            ('raw_records',) if build_lowlevel
            else ('raw_records', 'records', 'peaklets')),
        **common_opts)

def xenon1t_led(**kwargs):
    st = xenon1t_dali(**kwargs)
    st.context_config['check_available'] = ('raw_records', 'led_calibration')
    # Return a new context with only raw_records and led_calibration registered
    return st.new_context(
        replace=True,
        register=[straxen.RecordsFromPax, straxen.LEDCalibration],
        free_options=('channel_map',),
        config=st.config,
        storage=st.storage,
        **st.context_config)


def strax_nveto_hdm_test(dynamic_voltage_05V=False, output_folder='./strax_data'):
    nveto_common_opts = dict(
        register_all=[
            straxen.nveto_recorder,
            straxen.nveto_pulse_processing,
            # TPC plugins to avoid unused settings warning
            straxen.pulse_processing,
            straxen.peaklet_processing,
            straxen.peak_processing,
            straxen.event_processing
        ],
        store_run_fields=(
            'name', 'number',
            'reader.ini.name', 'tags.name',
            'start', 'end', 'livetime',
            'trigger.events_built'),
        check_available=('raw_records_prenv',
                         'raw_records_aqmonnv',
                         'raw_records_nv',
                         'lone_raw_records_nv',
                         'lone_raw_record_statistics_nv',
                         'records_nv',
                         'pulse_edges_nv',
                         'pulse_basics_nv'
                         ))

    # HdM test specific configurations;
    hdm_daqreader = dict(digitizer_sampling_resolution=2,
                         n_readout_threads=8,
                         coincidence_level=2,
                         )
    # HdM test specific configurations for 0.5 V dynamic range.
    hdm_0_5V = dict(hit_min_amplitude_nv=60,
                    voltage=0.5)

    if dynamic_voltage_05V:
        config = {**xnt_common_config, **hdm_daqreader, **hdm_0_5V}
    else:
        config = {**xnt_common_config, **hdm_daqreader}
    return strax.Context(
        storage=[
            strax.DataDirectory(
                '/dali/lgrandi/wenz/strax_data/HdMdata_strax_v0_9_0/strax_data',
                provide_run_metadata=False,
                readonly=True),
            strax.DataDirectory(output_folder,
                                provide_run_metadata=False)],
        config=config,
        **nveto_common_opts)
