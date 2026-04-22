#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"

#import "VOCDevice.h"

@implementation VOCDevice

- (instancetype)initWithObjectID:(CMIOObjectID)objectID streamID:(CMIOObjectID)streamID {
    self = [super init];
    _objectID = objectID;
    _stream = [[VOCStream alloc] initWithObjectID:streamID deviceID:objectID];
    return self;
}

- (Boolean)hasProperty:(CMIOObjectPropertyAddress const *)addr {
    switch (addr->mSelector) {
        case kCMIOObjectPropertyName:
        case kCMIOObjectPropertyManufacturer:
        case kCMIODevicePropertyModelUID:
        case kCMIODevicePropertyDeviceUID:
        case kCMIODevicePropertyTransportType:
        case kCMIODevicePropertyStreams:
        case kCMIODevicePropertyExcludeNonDALAccess:
        case kCMIODevicePropertyClientSyncDiscontinuity:
            return YES;
        default: return NO;
    }
}

- (OSStatus)getPropertyDataSize:(CMIOObjectPropertyAddress const *)addr
              qualifierDataSize:(UInt32)qSize
                  qualifierData:(const void *)qData
                          size:(UInt32 *)outSize {
    switch (addr->mSelector) {
        case kCMIOObjectPropertyName:
        case kCMIOObjectPropertyManufacturer:
        case kCMIODevicePropertyModelUID:
        case kCMIODevicePropertyDeviceUID:
            *outSize = sizeof(CFStringRef); break;
        case kCMIODevicePropertyTransportType:
        case kCMIODevicePropertyExcludeNonDALAccess:
        case kCMIODevicePropertyClientSyncDiscontinuity:
            *outSize = sizeof(UInt32); break;
        case kCMIODevicePropertyStreams:
            *outSize = sizeof(CMIOStreamID); break;
        default: return kCMIOHardwareUnknownPropertyError;
    }
    return noErr;
}

- (OSStatus)getPropertyData:(CMIOObjectPropertyAddress const *)addr
          qualifierDataSize:(UInt32)qSize
              qualifierData:(const void *)qData
                   dataSize:(UInt32)dataSize
               bytesWritten:(UInt32 *)outBytesWritten
                       data:(void *)outData {
    switch (addr->mSelector) {
        case kCMIOObjectPropertyName: {
            CFStringRef s = CFSTR("Video Overlay Camera");
            CFRetain(s);
            *(CFStringRef *)outData = s;
            *outBytesWritten = sizeof(CFStringRef);
            break;
        }
        case kCMIOObjectPropertyManufacturer: {
            CFStringRef s = CFSTR("VideoOverlay");
            CFRetain(s);
            *(CFStringRef *)outData = s;
            *outBytesWritten = sizeof(CFStringRef);
            break;
        }
        case kCMIODevicePropertyModelUID: {
            CFStringRef s = CFSTR("com.videooverlay.virtual-camera");
            CFRetain(s);
            *(CFStringRef *)outData = s;
            *outBytesWritten = sizeof(CFStringRef);
            break;
        }
        case kCMIODevicePropertyDeviceUID: {
            CFStringRef s = CFSTR("com.videooverlay.virtual-camera.device");
            CFRetain(s);
            *(CFStringRef *)outData = s;
            *outBytesWritten = sizeof(CFStringRef);
            break;
        }
        case kCMIODevicePropertyTransportType: {
            // 'virt' = virtual device transport type
            *(UInt32 *)outData = 0x76697274; // 'virt'
            *outBytesWritten = sizeof(UInt32);
            break;
        }
        case kCMIODevicePropertyExcludeNonDALAccess:
        case kCMIODevicePropertyClientSyncDiscontinuity: {
            *(UInt32 *)outData = 0;
            *outBytesWritten = sizeof(UInt32);
            break;
        }
        case kCMIODevicePropertyStreams: {
            *(CMIOStreamID *)outData = _stream.objectID;
            *outBytesWritten = sizeof(CMIOStreamID);
            break;
        }
        default: return kCMIOHardwareUnknownPropertyError;
    }
    return noErr;
}

@end

#pragma clang diagnostic pop
