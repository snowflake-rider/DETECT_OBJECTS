import platform

import AVFoundation as av


def find_cameras() -> list[tuple[int, str]]:
    if platform.system() != "Darwin":
        raise RuntimeError("This script supports macOS only.")

    device_types = [
        av.AVCaptureDeviceTypeBuiltInWideAngleCamera,
        av.AVCaptureDeviceTypeContinuityCamera,
        av.AVCaptureDeviceTypeDeskViewCamera,
        av.AVCaptureDeviceTypeExternal,
    ]
    discovery_session = (
        av.AVCaptureDeviceDiscoverySession
        .discoverySessionWithDeviceTypes_mediaType_position_(
            device_types,
            av.AVMediaTypeVideo,
            av.AVCaptureDevicePositionUnspecified,
        )
    )

    return [
        (index, str(device.localizedName()))
        for index, device in enumerate(discovery_session.devices())
    ]


def main() -> None:
    cameras = find_cameras()

    if not cameras:
        print("No cameras found.")
        return

    print("Available cameras:")
    for index, name in cameras:
        print(f"[{index}] {name}")


if __name__ == "__main__":
    main()
