import json
import os
import subprocess
import tempfile
import types

import natcap.invest
from natcap.invest import models
from natcap.invest import spec
import pywps
from pywps import Process, ComplexInput, LiteralInput, ComplexOutput, UOM
from pywps.validator.mode import MODE
from pywps.inout.formats import FORMATS

def generate_model_inputs(MODEL_SPEC):
    inputs = []  # model inputs may be files or literal types
    for model_input in MODEL_SPEC.inputs:

        min_occurs = 1 if model_input.required is True else 0
        input_kwargs = dict(
            identifier=model_input.id,
            title=model_input.name,
            abstract=model_input.about,
            workdir=None,  # workspace dir?
            min_occurs=min_occurs,
            max_occurs=1,
            mode=MODE.STRICT,
            translations=None  # Neat!
        )
        if (isinstance(model_input, spec.FileInput) or
                isinstance(model_input, spec.DirectoryInput)):
            if isinstance(model_input, spec.VectorInput):
                supported_formats = [FORMATS.GEOJSON]
            elif type(model_input) in {spec.SingleBandRasterInput, spec.RasterInput}:
                supported_formats = [FORMATS.GEOTIFF]
            elif isinstance(model_input, spec.CSVInput):
                supported_formats = [FORMATS.CSV]
            elif isinstance(model_input, spec.RasterOrVectorInput):
                supported_formats = [FORMATS.GEOTIFF, FORMATS.GEOJSON]
            elif isinstance(model_input, spec.DirectoryInput):
                supported_formats = []  # what to do here?

            # Unclear what to do in case of unspecified file type,
            # but this is not used by any invest model.
            # elif isinstance(model_input, spec.FileInput):
            #     pass
            inputs.append(ComplexInput(
                **input_kwargs,
                supported_formats=supported_formats
            ))
        else:
            data_type = {
                spec.NumberInput: 'float',
                spec.PercentInput: 'float',
                spec.RatioInput: 'float',
                spec.IntegerInput: 'integer',
                spec.StringInput: 'string',
                spec.OptionStringInput: 'string',
                spec.BooleanInput: 'boolean'  # ?
            }[type(model_input)]

            allowed_values = None
            if isinstance(model_input, spec.OptionStringInput):
                allowed_values = model_input.options

            uoms = None  # units of measurement
            if hasattr(model_input, 'units') and model_input.units:
                uoms = [str(model_input.units)]

            inputs.append(LiteralInput(
                **input_kwargs,
                data_type=data_type,
                uoms=uoms,
                allowed_values=allowed_values))
    return inputs


def generate_model_outputs(MODEL_SPEC):
    outputs = []
    for model_output in MODEL_SPEC.outputs:
        if isinstance(model_output, spec.VectorOutput):
            data_format = FORMATS.GEOJSON
        elif type(model_output) in {spec.SingleBandRasterOutput, spec.RasterOutput}:
            data_format = FORMATS.GEOTIFF
        elif isinstance(model_output, spec.CSVOutput):
            data_format = FORMATS.CSV
        elif isinstance(model_output, spec.FileOutput):
            data_format = FORMATS.CSV # placeholder
        elif isinstance(model_output, spec.DirectoryOutput):
            data_format = FORMATS.CSV # placeholder
        else:
            print(model_output)
        outputs.append(ComplexOutput(  # all model outputs are files
            identifier=model_output.id,
            title=model_output.id,
            supported_formats=[data_format],
            data_format=data_format,
            abstract=model_output.about))
    return outputs


def get_model_processes():
    model_processes = []
    for module in models.pyname_to_module.values():

        def handler(self, request: pywps.app.WPSRequest, response: pywps.response.basic.WPSResponse):

            # parse request.inputs into args dict
            args = request.inputs
            module.validate(args)
            module.execute(args)

            # set response values

        # dynamically make a class inherited from pywps.Process
        # to represent each invest model
        new_class = type(
            f'ExecuteInVEST_${module.MODEL_SPEC.model_id}',
            (Process,),
            {}
        )

        def __init__(self):
            print('__init__!')
            super(new_class, self).__init__(
                handler=handler,
                identifier=module.MODEL_SPEC.model_id,
                title=module.MODEL_SPEC.model_title,
                inputs=generate_model_inputs(module.MODEL_SPEC),
                outputs=generate_model_outputs(module.MODEL_SPEC))


        new_class.__init__ = __init__
        model_processes.append(new_class())

    return model_processes
