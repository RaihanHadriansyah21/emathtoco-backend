from tensorflow.keras.layers import Dense
from tensorflow.keras.models import load_model


class PatchedDense(Dense):
    def __init__(self, *args, **kwargs):
        kwargs.pop("quantization_config", None)
        super().__init__(*args, **kwargs)

    @classmethod
    def from_config(cls, config):
        config.pop("quantization_config", None)
        return super().from_config(config)


def load_mobilenet_model(model_path):

    model = load_model(
        model_path, compile=False, custom_objects={"Dense": PatchedDense}
    )

    return model
