from __future__ import annotations

import torch
import torch.nn as nn


class ConvBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False),
            nn.InstanceNorm2d(out_ch, affine=True),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.InstanceNorm2d(out_ch, affine=True),
            nn.LeakyReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class UNet2D(nn.Module):
    def __init__(self, in_channels: int, base: int = 32):
        super().__init__()
        self.enc1 = ConvBlock(in_channels, base)
        self.pool1 = nn.MaxPool2d(2)

        self.enc2 = ConvBlock(base, base * 2)
        self.pool2 = nn.MaxPool2d(2)

        self.enc3 = ConvBlock(base * 2, base * 4)
        self.pool3 = nn.MaxPool2d(2)

        self.bottleneck = ConvBlock(base * 4, base * 8)

        self.up3 = nn.ConvTranspose2d(base * 8, base * 4, 2, stride=2)
        self.dec3 = ConvBlock(base * 8, base * 4)

        self.up2 = nn.ConvTranspose2d(base * 4, base * 2, 2, stride=2)
        self.dec2 = ConvBlock(base * 4, base * 2)

        self.up1 = nn.ConvTranspose2d(base * 2, base, 2, stride=2)
        self.dec1 = ConvBlock(base * 2, base)

        self.out = nn.Conv2d(base, 1, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool1(e1))
        e3 = self.enc3(self.pool2(e2))

        b = self.bottleneck(self.pool3(e3))

        d3 = self.up3(b)
        d3 = torch.cat([d3, e3], dim=1)
        d3 = self.dec3(d3)

        d2 = self.up2(d3)
        d2 = torch.cat([d2, e2], dim=1)
        d2 = self.dec2(d2)

        d1 = self.up1(d2)
        d1 = torch.cat([d1, e1], dim=1)
        d1 = self.dec1(d1)

        return self.out(d1)


class ConvDropoutNormReLU(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int):
        super().__init__()
        self.conv = nn.Conv2d(
            in_channels,
            out_channels,
            kernel_size=3,
            stride=stride,
            padding=1,
            bias=True,
        )
        self.norm = nn.InstanceNorm2d(out_channels, eps=1e-5, affine=True)
        self.nonlin = nn.LeakyReLU(inplace=True)
        self.all_modules = nn.Sequential(self.conv, self.norm, self.nonlin)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.all_modules(x)


class StackedConvBlocks(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, initial_stride: int):
        super().__init__()
        self.convs = nn.Sequential(
            ConvDropoutNormReLU(in_channels, out_channels, stride=initial_stride),
            ConvDropoutNormReLU(out_channels, out_channels, stride=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.convs(x)


class Encoder(nn.Module):
    def __init__(self, in_channels: int, features_per_stage: list[int], strides: list[int]):
        super().__init__()
        stages: list[nn.Module] = []
        current_channels = in_channels
        for out_channels, stride in zip(features_per_stage, strides):
            block = StackedConvBlocks(current_channels, out_channels, initial_stride=stride)
            stages.append(nn.Sequential(block))
            current_channels = out_channels
        self.stages = nn.Sequential(*stages)

    def forward(self, x: torch.Tensor) -> list[torch.Tensor]:
        skips: list[torch.Tensor] = []
        for stage in self.stages:
            x = stage(x)
            skips.append(x)
        return skips


class Decoder(nn.Module):
    def __init__(self, encoder: Encoder, features_per_stage: list[int], num_classes: int):
        super().__init__()
        self.encoder = encoder

        transpconvs: list[nn.Module] = []
        stages: list[nn.Module] = []
        seg_layers: list[nn.Module] = []

        reversed_features = list(reversed(features_per_stage))
        lowres_channels = reversed_features[0]
        for skip_channels in reversed_features[1:]:
            transpconvs.append(
                nn.ConvTranspose2d(lowres_channels, skip_channels, kernel_size=2, stride=2)
            )
            stages.append(
                StackedConvBlocks(
                    in_channels=skip_channels * 2,
                    out_channels=skip_channels,
                    initial_stride=1,
                )
            )
            seg_layers.append(nn.Conv2d(skip_channels, num_classes, kernel_size=1))
            lowres_channels = skip_channels

        self.transpconvs = nn.ModuleList(transpconvs)
        self.stages = nn.ModuleList(stages)
        self.seg_layers = nn.ModuleList(seg_layers)

    def forward(self, skips: list[torch.Tensor]) -> torch.Tensor:
        x = skips[-1]
        reversed_skips = list(reversed(skips[:-1]))
        for idx, (transpconv, stage, seg_layer) in enumerate(
            zip(self.transpconvs, self.stages, self.seg_layers)
        ):
            x = transpconv(x)
            x = torch.cat([x, reversed_skips[idx]], dim=1)
            x = stage(x)
            seg = seg_layer(x)
        return seg


class PlainConvUNet2D(nn.Module):
    def __init__(self, in_channels: int = 4, num_classes: int = 4):
        super().__init__()
        features_per_stage = [32, 64, 128, 256, 512, 512]
        strides = [1, 2, 2, 2, 2, 2]
        self.encoder = Encoder(
            in_channels=in_channels,
            features_per_stage=features_per_stage,
            strides=strides,
        )
        self.decoder = Decoder(
            encoder=self.encoder,
            features_per_stage=features_per_stage,
            num_classes=num_classes,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skips = self.encoder(x)
        return self.decoder(skips)
