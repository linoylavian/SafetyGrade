import argparse
import torch
from raft import RAFT
from utils import InputPadder
DEVICE = 'cpu'

class OpticalFlowModel:
    @staticmethod
    def getmodel():
        """:return: the model for calculating optical flow of two photos"""
        parser = argparse.ArgumentParser()
        args = parser.parse_args()
        model = torch.nn.DataParallel(RAFT(args))
        model.load_state_dict(torch.load('raft-things.pth', map_location=DEVICE))
        model = model.module
        model.to(DEVICE)
        model.eval()
        return model

    @staticmethod
    def run2(image1, image2, model):
        """
        :param image1: first photo
        :param image2: second photo
        :param model: model for calculating optical flow of two photos
        :return: numpy array that represents the optical flow of two photos
        """
        with torch.no_grad():
            padder = InputPadder(image1.shape)
            image1, image2 = padder.pad(image1, image2)
            flow_low, flow_up = model(image1, image2, iters=20, test_mode=True)
            return flow_up.cpu().numpy()
