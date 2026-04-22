#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"

#import "VOCStream.h"
#import <CoreMediaIO/CMIOSampleBuffer.h>
#import <CoreMedia/CoreMedia.h>
#import <mach/mach_time.h>

static const int    kWidth    = 1280;
static const int    kHeight   = 720;
static const float  kFPS      = 30.0f;
static NSString *const kFrameFile = @"/tmp/voc_frame.bgra";
static NSString *const kSeqFile   = @"/tmp/voc_seq";

@implementation VOCStream {
    CMVideoFormatDescriptionRef _formatDesc;
    CFTypeRef                   _clock;      // from CMIOStreamClockCreate
    uint64_t                    _seqNum;
    uint64_t                    _lastFileSeq;
    NSData                     *_blankFrame;
}

- (instancetype)initWithObjectID:(CMIOObjectID)objectID deviceID:(CMIOObjectID)deviceID {
    self = [super init];
    _objectID = objectID;
    _deviceID = deviceID;
    _seqNum   = 0;
    _lastFileSeq = UINT64_MAX;

    CMVideoFormatDescriptionCreate(kCFAllocatorDefault,
                                   kCMPixelFormat_32BGRA,
                                   kWidth, kHeight, NULL, &_formatDesc);

    _frameQueue = dispatch_queue_create("com.videooverlay.frameq", DISPATCH_QUEUE_SERIAL);

    size_t sz = (size_t)(kWidth * kHeight * 4);
    void *blank = calloc(1, sz);
    _blankFrame = [NSData dataWithBytesNoCopy:blank length:sz freeWhenDone:YES];

    return self;
}

- (void)startFrameDelivery {
    CMIOStreamClockCreate(kCFAllocatorDefault,
                          CFSTR("VideoOverlayClock"),
                          (__bridge void *)self,
                          CMTimeMake(1, (int32_t)kFPS),
                          100, 10,
                          &_clock);

    uint64_t interval = (uint64_t)(1e9 / kFPS);
    _frameTimer = dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER, 0, 0, _frameQueue);
    dispatch_source_set_timer(_frameTimer,
                              dispatch_time(DISPATCH_TIME_NOW, 0),
                              interval, interval / 4);
    dispatch_source_set_event_handler(_frameTimer, ^{ [self deliverFrame]; });
    dispatch_resume(_frameTimer);
}

- (void)stopFrameDelivery {
    if (_frameTimer) {
        dispatch_source_cancel(_frameTimer);
        _frameTimer = nil;
    }
    if (_clock) {
        CMIOStreamClockPostTimingEvent(CMTimeMake(0, 1), mach_absolute_time(), true, _clock);
        CFRelease(_clock);
        _clock = NULL;
    }
}

- (void)deliverFrame {
    if (!_queue) return;

    // Check if there's a new frame file
    uint64_t fileSeq = 0;
    NSData *seqData = [NSData dataWithContentsOfFile:kSeqFile];
    if (seqData && seqData.length >= 8) {
        memcpy(&fileSeq, seqData.bytes, 8);
    }

    NSData *frameData = nil;
    if (fileSeq != _lastFileSeq) {
        NSData *d = [NSData dataWithContentsOfFile:kFrameFile];
        if (d && (NSInteger)d.length == kWidth * kHeight * 4) {
            frameData = d;
            _lastFileSeq = fileSeq;
        }
    }
    if (!frameData) frameData = _blankFrame;

    // Allocate pixel buffer and copy frame data in
    CVPixelBufferRef pixelBuf = NULL;
    NSDictionary *attrs = @{
        (NSString*)kCVPixelBufferPixelFormatTypeKey: @(kCMPixelFormat_32BGRA),
        (NSString*)kCVPixelBufferWidthKey:            @(kWidth),
        (NSString*)kCVPixelBufferHeightKey:           @(kHeight),
        (NSString*)kCVPixelBufferIOSurfacePropertiesKey: @{}
    };
    CVReturn cvErr = CVPixelBufferCreate(kCFAllocatorDefault,
                                        kWidth, kHeight,
                                        kCMPixelFormat_32BGRA,
                                        (__bridge CFDictionaryRef)attrs,
                                        &pixelBuf);
    if (cvErr != kCVReturnSuccess || !pixelBuf) return;

    CVPixelBufferLockBaseAddress(pixelBuf, 0);
    void *dst = CVPixelBufferGetBaseAddress(pixelBuf);
    if (dst) memcpy(dst, frameData.bytes, (size_t)(kWidth * kHeight * 4));
    CVPixelBufferUnlockBaseAddress(pixelBuf, 0);

    // Timing: use host clock
    CMTime pts = CMClockGetTime(CMClockGetHostTimeClock());
    if (_clock) {
        CMIOStreamClockPostTimingEvent(pts, mach_absolute_time(), true, _clock);
    }

    CMSampleTimingInfo timing = {
        .duration              = CMTimeMake(1, (int32_t)kFPS),
        .presentationTimeStamp = pts,
        .decodeTimeStamp       = kCMTimeInvalid
    };

    CMSampleBufferRef sampleBuf = NULL;
    OSStatus err = CMIOSampleBufferCreateForImageBuffer(
        kCFAllocatorDefault,
        pixelBuf,
        _formatDesc,
        &timing,
        _seqNum++,
        kCMIOSampleBufferNoDiscontinuities,
        &sampleBuf
    );
    CVPixelBufferRelease(pixelBuf);

    if (err != noErr || !sampleBuf) return;

    CMSimpleQueueEnqueue(_queue, sampleBuf);
    if (_alteredProc) {
        _alteredProc(_objectID, sampleBuf, _alteredRefCon);
    }
    CFRelease(sampleBuf);
}

#pragma mark - Property support

- (Boolean)hasProperty:(CMIOObjectPropertyAddress const *)addr {
    switch (addr->mSelector) {
        case kCMIOStreamPropertyDirection:
        case kCMIOStreamPropertyFormatDescription:
        case kCMIOStreamPropertyFormatDescriptions:
        case kCMIOStreamPropertyFrameRate:
        case kCMIOStreamPropertyFrameRates:
        case kCMIOStreamPropertyMinimumFrameRate:
        case kCMIOStreamPropertyFrameRateRanges:
        case kCMIOObjectPropertyName:
        case kCMIOObjectPropertyManufacturer:
            return YES;
        default: return NO;
    }
}

- (OSStatus)getPropertyDataSize:(CMIOObjectPropertyAddress const *)addr
              qualifierDataSize:(UInt32)qSize
                  qualifierData:(const void *)qData
                          size:(UInt32 *)outSize {
    switch (addr->mSelector) {
        case kCMIOStreamPropertyDirection:
        case kCMIOStreamPropertyNoDataTimeoutInMSec:
            *outSize = sizeof(UInt32); break;
        case kCMIOStreamPropertyFrameRate:
        case kCMIOStreamPropertyMinimumFrameRate:
            *outSize = sizeof(Float64); break;
        case kCMIOStreamPropertyFormatDescription:
            *outSize = sizeof(CMFormatDescriptionRef); break;
        case kCMIOStreamPropertyFormatDescriptions:
        case kCMIOStreamPropertyFrameRates:
        case kCMIOStreamPropertyFrameRateRanges:
            *outSize = sizeof(CFArrayRef); break;
        case kCMIOObjectPropertyName:
        case kCMIOObjectPropertyManufacturer:
            *outSize = sizeof(CFStringRef); break;
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
        case kCMIOStreamPropertyDirection: {
            *(UInt32 *)outData = 1;
            *outBytesWritten = sizeof(UInt32);
            break;
        }
        case kCMIOStreamPropertyFrameRate:
        case kCMIOStreamPropertyMinimumFrameRate: {
            *(Float64 *)outData = kFPS;
            *outBytesWritten = sizeof(Float64);
            break;
        }
        case kCMIOStreamPropertyFormatDescription: {
            CFRetain(_formatDesc);
            *(CMFormatDescriptionRef *)outData = _formatDesc;
            *outBytesWritten = sizeof(CMFormatDescriptionRef);
            break;
        }
        case kCMIOStreamPropertyFormatDescriptions: {
            CFArrayRef arr = CFArrayCreate(NULL, (const void **)&_formatDesc, 1, &kCFTypeArrayCallBacks);
            *(CFArrayRef *)outData = arr;
            *outBytesWritten = sizeof(CFArrayRef);
            break;
        }
        case kCMIOStreamPropertyFrameRates: {
            Float64 fps = kFPS;
            CFNumberRef num = CFNumberCreate(NULL, kCFNumberFloat64Type, &fps);
            CFArrayRef arr = CFArrayCreate(NULL, (const void **)&num, 1, &kCFTypeArrayCallBacks);
            CFRelease(num);
            *(CFArrayRef *)outData = arr;
            *outBytesWritten = sizeof(CFArrayRef);
            break;
        }
        case kCMIOStreamPropertyFrameRateRanges: {
            AudioValueRange range = { .mMinimum = kFPS, .mMaximum = kFPS };
            CFDataRef d = CFDataCreate(NULL, (const UInt8 *)&range, sizeof(range));
            CFArrayRef arr = CFArrayCreate(NULL, (const void **)&d, 1, &kCFTypeArrayCallBacks);
            CFRelease(d);
            *(CFArrayRef *)outData = arr;
            *outBytesWritten = sizeof(CFArrayRef);
            break;
        }
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
        default: return kCMIOHardwareUnknownPropertyError;
    }
    return noErr;
}

@end

#pragma clang diagnostic pop
