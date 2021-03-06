#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Predict operation for losito: runs DPPP to predict a sky model with corruptions
"""
import os
from ..lib_io import logger

logger.debug('Loading PREDICT module.')

def _run_parser(obs, parser, step):
    outputColumn = parser.getstr( step, 'outputColumn', 'DATA')
    predictType = parser.getstr( step, 'predictType', 'h5parmpredict')
    resetWeights = parser.getbool( step, 'resetWeights', True)
    ncpu = parser.getint( '_global', 'ncpu', 0)
    parser.checkSpelling( step, ['outputColumn', 'resetWeights',
                                 'predictType'])
    return run(obs, outputColumn, predictType, resetWeights, ncpu)


def run(obs, outputColumn='DATA', predictType='h5parmpredict',
        resetWeights=True, ncpu=0):
    """
    Runs DPPP to predict a sky model. Prediction type h5parmpredict will
    apply corruptions stored in a .h5parmdb (default).
    Prediction type predict will generate uncorrupted ground truth
    visibilities.

    Parameters
    ----------
    obs : Observation object
        Input obs object.
    outputColumn : str, optional
        Name of output column
    predictType : str, optional
        Type of DPPP predict command
    resetWeights : bool, optional
        Whether to reset the entries in WEIGHT_SPECTRUM column
    ncpu : int, optional
        Number of cpu to use, by default all available.
    """
    s = obs.scheduler
    # reset weights if specified (default).
    if resetWeights:
        logger.info('Reset entries in WEIGHT_SPECTRUM...')
        for ms in obs:
            cmd = 'taql UPDATE {0} SET WEIGHT_SPECTRUM=1.0'.format(ms.ms_filename)
            # TODO: more accurate weights
            s.add(cmd, log='taql_reset_weights', processors=1)
    s.run()
    # Make sourcedb from sky model
    obs.make_sourcedb()

    # TODO: Reset beam keyword using DPPP step setbeam
    # TODO: move most of this to observation class
    # Set parset parameters and write parset to file
    if not 'predict' in obs.parset_parameters['steps']:
        obs.parset_parameters['steps'].insert(0,'predict')
    obs.parset_parameters['numthreads'] = ncpu
    obs.parset_parameters['predict.type'] = predictType
    obs.parset_parameters['predict.sourcedb'] = obs.sourcedb_filename
    obs.parset_parameters['predict.operation'] = 'replace'
    obs.parset_parameters['msout.datacolumn'] = outputColumn
    obs.make_parset()
    # Ensure that the LOFAR_APPLIED_BEAM_MODE keyword is unset (otherwise DPPP may
    # complain that the beam has already been applied)
    obs.reset_beam_keyword(outputColumn)

    # Run DPPP
    for ms in obs:
        cmd = 'DPPP {} msin={}'.format(obs.parset_filename, ms.ms_filename)
        # TODO if ms filename contains dirname split
        msname = os.path.split(ms.ms_filename)[1]
        s.add(cmd, commandType='DPPP', log='predict_'+msname, processors='max')
    logger.info('Predict visibilities...')
    s.run(check=True)

    # Ensure again that the LOFAR_APPLIED_BEAM_MODE keyword is unset
    obs.reset_beam_keyword(outputColumn)

    # Return result
    return 0
