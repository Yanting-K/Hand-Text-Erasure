import torch
from torch import nn
from torch import autograd
import torch.nn.functional as F
from tensorboardX import SummaryWriter
from models.discriminator import Discriminator_STE
from PIL import Image
import numpy as np

def gram_matrix(feat):
    # https://github.com/pytorch/examples/blob/master/fast_neural_style/neural_style/utils.py
    (b, ch, h, w) = feat.size()
    feat = feat.view(b, ch, h * w)
    feat_t = feat.transpose(1, 2)
    gram = torch.bmm(feat, feat_t) / (ch * h * w)
    return gram

def visual(image):
    im = image.transpose(1,2).transpose(2,3).detach().cpu().numpy()
    Image.fromarray(im[0].astype(np.uint8)).show()

def dice_loss(input, target):
    input = torch.sigmoid(input)

    input = input.contiguous().view(input.size()[0], -1)
    target = target.contiguous().view(target.size()[0], -1)
    
    input = input 
    target = target

    a = torch.sum(input * target, 1)
    b = torch.sum(input * input, 1) + 0.001
    c = torch.sum(target * target, 1) + 0.001
    d = (2 * a) / (b + c)
    dice_loss = torch.mean(d)
    return 1 - dice_loss

class LossWithGAN_STE(nn.Module):
    def __init__(self, logPath, extractor, Lamda, lr, betasInit=(0.5, 0.9)):
        super(LossWithGAN_STE, self).__init__()
        self.l1 = nn.L1Loss()
        self.extractor = extractor
        self.discriminator = Discriminator_STE(3)    ## local_global sn patch gan
        self.D_optimizer = torch.optim.Adam(self.discriminator.parameters(), lr=lr, betas=betasInit)
        self.cudaAvailable = torch.cuda.is_available()
        self.numOfGPUs = torch.cuda.device_count()
        self.lamda = Lamda
        self.writer = SummaryWriter(logPath)

    def forward(self, input, mask, x_o1,x_o2,x_o3,output,mm, gt, count, epoch):
        self.discriminator.zero_grad()
        D_real = self.discriminator(gt, mask)
        D_real = D_real.mean().sum() * -1
        D_fake = self.discriminator(output, mask)
        D_fake = D_fake.mean().sum() * 1
        D_loss = torch.mean(F.relu(1.+D_real)) + torch.mean(F.relu(1.+D_fake))  #SN-patch-GAN loss
        D_fake = -torch.mean(D_fake)     #  SN-Patch-GAN loss

        self.D_optimizer.zero_grad()
        D_loss.backward(retain_graph=True)
        self.D_optimizer.step()

        self.writer.add_scalar('LossD/Discrinimator loss', D_loss.item(), count)
        
        output_comp = mask * input + (1 - mask) * output
       # import pdb;pdb.set_trace()
        holeLoss = 10 * self.l1((1 - mask) * output, (1 - mask) * gt)
        validAreaLoss = 2*self.l1(mask * output, mask * gt)  

        mask_loss = dice_loss(mm, 1-mask)
        ### MSR loss ###
        masks_a = F.interpolate(mask, scale_factor=0.25)
        masks_b = F.interpolate(mask, scale_factor=0.5)
        imgs1 = F.interpolate(gt, scale_factor=0.25)
        imgs2 = F.interpolate(gt, scale_factor=0.5)
        msrloss = 8 * self.l1((1-mask)*x_o3,(1-mask)*gt) + 0.8*self.l1(mask*x_o3, mask*gt)+\
                    6 * self.l1((1-masks_b)*x_o2,(1-masks_b)*imgs2)+1*self.l1(masks_b*x_o2,masks_b*imgs2)+\
                    5 * self.l1((1-masks_a)*x_o1,(1-masks_a)*imgs1)+0.8*self.l1(masks_a*x_o1,masks_a*imgs1)

        feat_output_comp = self.extractor(output_comp)
        feat_output = self.extractor(output)
        feat_gt = self.extractor(gt)

        prcLoss = 0.0
        for i in range(3):
            prcLoss += 0.01 * self.l1(feat_output[i], feat_gt[i])
            prcLoss += 0.01 * self.l1(feat_output_comp[i], feat_gt[i])

        styleLoss = 0.0
        for i in range(3):
            styleLoss += 120 * self.l1(gram_matrix(feat_output[i]),
                                          gram_matrix(feat_gt[i]))
            styleLoss += 120 * self.l1(gram_matrix(feat_output_comp[i]),
                                          gram_matrix(feat_gt[i]))
        """ if self.numOfGPUs > 1:
            holeLoss = holeLoss.sum() / self.numOfGPUs
            validAreaLoss = validAreaLoss.sum() / self.numOfGPUs
            prcLoss = prcLoss.sum() / self.numOfGPUs
            styleLoss = styleLoss.sum() / self.numOfGPUs """
        self.writer.add_scalar('LossG/Hole loss', holeLoss.item(), count)    
        self.writer.add_scalar('LossG/Valid loss', validAreaLoss.item(), count) 
        self.writer.add_scalar('LossG/msr loss', msrloss.item(), count)   
        self.writer.add_scalar('LossPrc/Perceptual loss', prcLoss.item(), count)    
        self.writer.add_scalar('LossStyle/style loss', styleLoss.item(), count)

        GLoss = msrloss+ holeLoss + validAreaLoss+ prcLoss + styleLoss + 0.1 * D_fake + mask_loss
        self.writer.add_scalar('Generator/Joint loss', GLoss.item(), count)    
        return GLoss.sum()#,self.D_optimizer
    
