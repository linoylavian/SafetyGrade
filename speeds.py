import torch
from efficientnet_pytorch import EfficientNet

class SpeedModel:
    def __init__(self):
        """create EfficientNet model, and match it to the trained model in file 'b0.pth'"""
        self.MODEL_F = 'b0.pth'
        self.device = 'cpu'
        V = 0      # version of efficientnet
        IN_C = 2   # number of input channels
        NUM_C = 1  # number of classes to predict
        self.model = EfficientNet.from_pretrained(f'efficientnet-b{V}', in_channels=IN_C, num_classes=NUM_C)
        state = torch.load(self.MODEL_F, map_location='cpu')
        self.model.load_state_dict(state)
        self.model.to(self.device)

    def inference(self, nparr):
        i = torch.from_numpy(nparr).to(self.device)
        pred = self.model(i)
        del i
        torch.cuda.empty_cache()
        return pred

    def item(self, nparr):
        """
        :param nparr: numpy array of optical flow of to photos
        :return: size of speed in the moment of the photo
        """
        y_hat = self.inference(nparr).item()
        label = round(y_hat, 2)
        speed = label * 1.609344 * 5
        return speed
