import torch
import torch.nn as nn
import torch.nn.functional as F

class DoubleConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv3d(in_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm3d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv3d(out_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm3d(out_ch),
            nn.ReLU(inplace=True)
        )
    def forward(self, x):
        return self.conv(x)

class UNetDecoder(nn.Module):
    def __init__(self, in_channels=64, out_channels=1):
        super().__init__()
        # Upsampling progressif : 7 -> 14 -> 28 -> 56 -> 64
        self.up1 = nn.ConvTranspose3d(in_channels, 64, kernel_size=2, stride=2)
        self.conv1 = DoubleConv(64, 64)
        
        self.up2 = nn.ConvTranspose3d(64, 32, kernel_size=2, stride=2)
        self.conv2 = DoubleConv(32, 32)
        
        self.up3 = nn.ConvTranspose3d(32, 16, kernel_size=2, stride=2)
        self.conv3 = DoubleConv(16, 16)
        
        self.up4 = nn.Upsample(size=64, mode='trilinear', align_corners=False)
        self.final = nn.Conv3d(16, out_channels, kernel_size=1)

    def forward(self, x):
        # x : (B, 64, 7, 7, 7)
        x = self.up1(x)      # (B, 64, 14, 14, 14)
        x = self.conv1(x)    # (B, 64, 14, 14, 14)
        
        x = self.up2(x)      # (B, 32, 28, 28, 28)
        x = self.conv2(x)    # (B, 32, 28, 28, 28)
        
        x = self.up3(x)      # (B, 16, 56, 56, 56)
        x = self.conv3(x)    # (B, 16, 56, 56, 56)
        
        x = self.up4(x)      # (B, 16, 64, 64, 64)
        x = self.final(x)    # (B, 1, 64, 64, 64)
        return x