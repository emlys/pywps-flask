import json
import os
import subprocess
import tempfile
import types

import natcap.invest
from natcap.invest import models
from natcap.invest import spec
from pywps import Process, ComplexInput, LiteralOutput, Format, UOM


def generate_model_inputs(MODEL_SPEC):
    inputs = []  # model inputs may be files or literal types
    for model_input in module.MODEL_SPEC.inputs:

        min_occurs = 1 if model_input.required is True else 0
        input_kwargs = dict(
            identifier=model_input.id,
            title=model_input.title,
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
                supported_formats = [Formats.GEOJSON]
            elif type(model_input) in {spec.SingleBandRasterInput, spec.RasterInput}:
                supported_formats = [Formats.GEOTIFF]
            elif isinstance(model_input, spec.CSVInput):
                supported_formats = [Formats.CSV]
            elif isinstance(model_input, spec.RasterOrVectorInput):
                supported_formats = [Formats.GEOTIFF, Formats.GEOJSON]
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
                spec.RatioInput: 'float'
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
    for model_output in module.MODEL_SPEC.outputs:
        if isinstance(model_input, spec.VectorInput):
            data_format = [Formats.GEOJSON]
        elif type(model_input) in {spec.SingleBandRasterInput, spec.RasterInput}:
            data_format = [Formats.GEOTIFF]
        elif isinstance(model_input, spec.CSVInput):
            data_format = [Formats.CSV]
        elif isinstance(model_input, spec.FileOutput):
            data_format = [Formats.HTML]
        outputs.append(ComplexOutput(  # all model outputs are files
            identifier=model_output.id,
            title=model_output.id,
            data_format=data_format,
            abstract=model_output.about))
    return outputs


def get_model_processes():
    model_processes = []
    for model_id, module in models.model_id_to_module:

        def handler(self, request: pywps.app.WPSRequest, response: pywps.app.WPSResponse):

            # parse request.inputs into args dict
            args = request.inputs
            module.validate(args)
            module.execute(args)

            # set response values


        def init(self):
            super().__init__(
                handler=handler,
                identifier=module.MODEL_SPEC.model_id,
                title=module.MODEL_SPEC.model_title,
                inputs=generate_model_inputs(module.MODEL_SPEC),
                outputs=generate_model_outputs(module.MODEL_SPEC))

        # dynamically make a class inherited from pywps.Process
        # to represent each invest model
        model_processes.append(type(
            name=f'ExecuteInVEST_${module.MODEL_SPEC.model_id}',
            bases=(Process,),
            attrs=dict(__init__=init)))

    return model_processes
