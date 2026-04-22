#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"

#import "VOCPlugIn.h"
#import <CoreMediaIO/CMIOHardwarePlugIn.h>

static const CMIOObjectID kPlugInID = 1;
static const CMIOObjectID kDeviceID = 2;
static const CMIOObjectID kStreamID = 3;

// Forward declarations
static HRESULT   PlugIn_QueryInterface(void *self, REFIID iid, LPVOID *ppv);
static ULONG     PlugIn_AddRef(void *self);
static ULONG     PlugIn_Release(void *self);
static OSStatus  PlugIn_Initialize(CMIOHardwarePlugInRef ref);
static OSStatus  PlugIn_InitializeWithObjectID(CMIOHardwarePlugInRef ref, CMIOObjectID objectID);
static OSStatus  PlugIn_Teardown(CMIOHardwarePlugInRef ref);
static void      PlugIn_ObjectShow(CMIOHardwarePlugInRef ref, CMIOObjectID id);
static Boolean   PlugIn_ObjectHasProperty(CMIOHardwarePlugInRef ref, CMIOObjectID id, const CMIOObjectPropertyAddress *addr);
static OSStatus  PlugIn_ObjectIsPropertySettable(CMIOHardwarePlugInRef ref, CMIOObjectID id, const CMIOObjectPropertyAddress *addr, Boolean *outSettable);
static OSStatus  PlugIn_ObjectGetPropertyDataSize(CMIOHardwarePlugInRef ref, CMIOObjectID id, const CMIOObjectPropertyAddress *addr, UInt32 qSize, const void *qData, UInt32 *outSize);
static OSStatus  PlugIn_ObjectGetPropertyData(CMIOHardwarePlugInRef ref, CMIOObjectID id, const CMIOObjectPropertyAddress *addr, UInt32 qSize, const void *qData, UInt32 dSize, UInt32 *outWritten, void *outData);
static OSStatus  PlugIn_ObjectSetPropertyData(CMIOHardwarePlugInRef ref, CMIOObjectID id, const CMIOObjectPropertyAddress *addr, UInt32 qSize, const void *qData, UInt32 dSize, const void *data);
static OSStatus  PlugIn_DeviceSuspend(CMIOHardwarePlugInRef ref, CMIODeviceID devID);
static OSStatus  PlugIn_DeviceResume(CMIOHardwarePlugInRef ref, CMIODeviceID devID);
static OSStatus  PlugIn_DeviceStartStream(CMIOHardwarePlugInRef ref, CMIODeviceID devID, CMIOStreamID streamID);
static OSStatus  PlugIn_DeviceStopStream(CMIOHardwarePlugInRef ref, CMIODeviceID devID, CMIOStreamID streamID);
static OSStatus  PlugIn_DeviceProcessAVCCommand(CMIOHardwarePlugInRef ref, CMIODeviceID devID, CMIODeviceAVCCommand *cmd);
static OSStatus  PlugIn_DeviceProcessRS422Command(CMIOHardwarePlugInRef ref, CMIODeviceID devID, CMIODeviceRS422Command *cmd);
static OSStatus  PlugIn_StreamCopyBufferQueue(CMIOHardwarePlugInRef ref, CMIOStreamID streamID, CMIODeviceStreamQueueAlteredProc alteredProc, void *alteredRefCon, CMSimpleQueueRef *outQueue);
static OSStatus  PlugIn_StreamDeckPlay(CMIOHardwarePlugInRef ref, CMIOStreamID streamID);
static OSStatus  PlugIn_StreamDeckStop(CMIOHardwarePlugInRef ref, CMIOStreamID streamID);
static OSStatus  PlugIn_StreamDeckJog(CMIOHardwarePlugInRef ref, CMIOStreamID streamID, SInt32 speed);
static OSStatus  PlugIn_StreamDeckCueTo(CMIOHardwarePlugInRef ref, CMIOStreamID streamID, Float64 frameNumber, Boolean playOnCue);

static CMIOHardwarePlugInInterface gPlugInInterface = {
    NULL,
    PlugIn_QueryInterface,
    PlugIn_AddRef,
    PlugIn_Release,
    PlugIn_Initialize,
    PlugIn_InitializeWithObjectID,
    PlugIn_Teardown,
    PlugIn_ObjectShow,
    PlugIn_ObjectHasProperty,
    PlugIn_ObjectIsPropertySettable,
    PlugIn_ObjectGetPropertyDataSize,
    PlugIn_ObjectGetPropertyData,
    PlugIn_ObjectSetPropertyData,
    PlugIn_DeviceSuspend,
    PlugIn_DeviceResume,
    PlugIn_DeviceStartStream,
    PlugIn_DeviceStopStream,
    PlugIn_DeviceProcessAVCCommand,
    PlugIn_DeviceProcessRS422Command,
    PlugIn_StreamCopyBufferQueue,
    PlugIn_StreamDeckPlay,
    PlugIn_StreamDeckStop,
    PlugIn_StreamDeckJog,
    PlugIn_StreamDeckCueTo
};

typedef struct { CMIOHardwarePlugInInterface *interface; CFUUIDRef factoryID; UInt32 refCount; } PlugInWrapper;
static PlugInWrapper gWrapper = { &gPlugInInterface, NULL, 1 };

// ----------------------------------------------------------------------------

@implementation VOCPlugIn

+ (VOCPlugIn *)shared {
    static VOCPlugIn *s;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ s = [VOCPlugIn new]; });
    return s;
}

- (void)initializeWithObjectID:(CMIOObjectID)objectID {
    _objectID = objectID;
    _device = [[VOCDevice alloc] initWithObjectID:kDeviceID streamID:kStreamID];
}

@end

// ----------------------------------------------------------------------------

static HRESULT PlugIn_QueryInterface(void *self, REFIID iid, LPVOID *ppv) {
    CFUUIDRef uuid = CFUUIDCreateFromUUIDBytes(NULL, iid);
    if (CFEqual(uuid, kCMIOHardwarePlugInTypeID) || CFEqual(uuid, IUnknownUUID)) {
        *ppv = &gWrapper;
        CFRelease(uuid);
        PlugIn_AddRef(self);
        return S_OK;
    }
    CFRelease(uuid);
    *ppv = NULL;
    return E_NOINTERFACE;
}

static ULONG PlugIn_AddRef(void *self)  { return ++((PlugInWrapper *)self)->refCount; }
static ULONG PlugIn_Release(void *self) { return --((PlugInWrapper *)self)->refCount; }
static OSStatus PlugIn_Initialize(CMIOHardwarePlugInRef ref) { return noErr; }

static OSStatus PlugIn_InitializeWithObjectID(CMIOHardwarePlugInRef ref, CMIOObjectID objectID) {
    [[VOCPlugIn shared] initializeWithObjectID:objectID];
    // Register our device with the CMIO system
    CMIOObjectID devID = kDeviceID;
    CMIOObjectsPublishedAndDied(ref, kCMIOObjectSystemObject, 1, &devID, 0, NULL);
    return noErr;
}

static OSStatus PlugIn_Teardown(CMIOHardwarePlugInRef ref) {
    [[VOCPlugIn shared].device.stream stopFrameDelivery];
    return noErr;
}

static void PlugIn_ObjectShow(CMIOHardwarePlugInRef ref, CMIOObjectID id) {}

static Boolean PlugIn_ObjectHasProperty(CMIOHardwarePlugInRef ref, CMIOObjectID id, const CMIOObjectPropertyAddress *addr) {
    VOCPlugIn *p = [VOCPlugIn shared];
    if (id == p.objectID) {
        return addr->mSelector == kCMIOObjectPropertyOwnedObjects;
    }
    if (id == p.device.objectID)        return [p.device hasProperty:addr];
    if (id == p.device.stream.objectID) return [p.device.stream hasProperty:addr];
    return NO;
}

static OSStatus PlugIn_ObjectIsPropertySettable(CMIOHardwarePlugInRef ref, CMIOObjectID id, const CMIOObjectPropertyAddress *addr, Boolean *outSettable) {
    *outSettable = NO;
    return noErr;
}

static OSStatus PlugIn_ObjectGetPropertyDataSize(CMIOHardwarePlugInRef ref, CMIOObjectID id, const CMIOObjectPropertyAddress *addr, UInt32 qSize, const void *qData, UInt32 *outSize) {
    VOCPlugIn *p = [VOCPlugIn shared];
    if (id == p.objectID) {
        if (addr->mSelector == kCMIOObjectPropertyOwnedObjects) {
            *outSize = sizeof(CMIOObjectID);
            return noErr;
        }
        return kCMIOHardwareUnknownPropertyError;
    }
    if (id == p.device.objectID)        return [p.device getPropertyDataSize:addr qualifierDataSize:qSize qualifierData:qData size:outSize];
    if (id == p.device.stream.objectID) return [p.device.stream getPropertyDataSize:addr qualifierDataSize:qSize qualifierData:qData size:outSize];
    return kCMIOHardwareBadObjectError;
}

static OSStatus PlugIn_ObjectGetPropertyData(CMIOHardwarePlugInRef ref, CMIOObjectID id, const CMIOObjectPropertyAddress *addr, UInt32 qSize, const void *qData, UInt32 dSize, UInt32 *outWritten, void *outData) {
    VOCPlugIn *p = [VOCPlugIn shared];
    if (id == p.objectID) {
        if (addr->mSelector == kCMIOObjectPropertyOwnedObjects) {
            *(CMIOObjectID *)outData = kDeviceID;
            *outWritten = sizeof(CMIOObjectID);
            return noErr;
        }
        return kCMIOHardwareUnknownPropertyError;
    }
    if (id == p.device.objectID)        return [p.device getPropertyData:addr qualifierDataSize:qSize qualifierData:qData dataSize:dSize bytesWritten:outWritten data:outData];
    if (id == p.device.stream.objectID) return [p.device.stream getPropertyData:addr qualifierDataSize:qSize qualifierData:qData dataSize:dSize bytesWritten:outWritten data:outData];
    return kCMIOHardwareBadObjectError;
}

static OSStatus PlugIn_ObjectSetPropertyData(CMIOHardwarePlugInRef ref, CMIOObjectID id, const CMIOObjectPropertyAddress *addr, UInt32 qSize, const void *qData, UInt32 dSize, const void *data) {
    return kCMIOHardwareUnsupportedOperationError;
}

static OSStatus PlugIn_DeviceSuspend(CMIOHardwarePlugInRef ref, CMIODeviceID devID) { return noErr; }
static OSStatus PlugIn_DeviceResume(CMIOHardwarePlugInRef ref, CMIODeviceID devID)  { return noErr; }

static OSStatus PlugIn_DeviceStartStream(CMIOHardwarePlugInRef ref, CMIODeviceID devID, CMIOStreamID streamID) {
    [[VOCPlugIn shared].device.stream startFrameDelivery];
    return noErr;
}

static OSStatus PlugIn_DeviceStopStream(CMIOHardwarePlugInRef ref, CMIODeviceID devID, CMIOStreamID streamID) {
    [[VOCPlugIn shared].device.stream stopFrameDelivery];
    return noErr;
}

static OSStatus PlugIn_DeviceProcessAVCCommand(CMIOHardwarePlugInRef ref, CMIODeviceID devID, CMIODeviceAVCCommand *cmd)      { return kCMIOHardwareUnsupportedOperationError; }
static OSStatus PlugIn_DeviceProcessRS422Command(CMIOHardwarePlugInRef ref, CMIODeviceID devID, CMIODeviceRS422Command *cmd)  { return kCMIOHardwareUnsupportedOperationError; }

static OSStatus PlugIn_StreamCopyBufferQueue(CMIOHardwarePlugInRef ref, CMIOStreamID streamID, CMIODeviceStreamQueueAlteredProc alteredProc, void *alteredRefCon, CMSimpleQueueRef *outQueue) {
    VOCStream *stream = [VOCPlugIn shared].device.stream;
    if (stream.objectID != streamID) return kCMIOHardwareBadObjectError;

    stream.alteredProc   = alteredProc;
    stream.alteredRefCon = alteredRefCon;

    CMSimpleQueueRef q = NULL;
    CMSimpleQueueCreate(kCFAllocatorDefault, 35, &q);
    stream.queue = q;
    *outQueue = q;
    return noErr;
}

static OSStatus PlugIn_StreamDeckPlay(CMIOHardwarePlugInRef ref, CMIOStreamID s)                                { return kCMIOHardwareUnsupportedOperationError; }
static OSStatus PlugIn_StreamDeckStop(CMIOHardwarePlugInRef ref, CMIOStreamID s)                                { return kCMIOHardwareUnsupportedOperationError; }
static OSStatus PlugIn_StreamDeckJog(CMIOHardwarePlugInRef ref, CMIOStreamID s, SInt32 speed)                   { return kCMIOHardwareUnsupportedOperationError; }
static OSStatus PlugIn_StreamDeckCueTo(CMIOHardwarePlugInRef ref, CMIOStreamID s, Float64 f, Boolean b)         { return kCMIOHardwareUnsupportedOperationError; }

// Factory function referenced in Info.plist
void *VOCPlugInFactory(CFAllocatorRef allocator, CFUUIDRef requestedTypeUUID) {
    if (!CFEqual(requestedTypeUUID, kCMIOHardwarePlugInTypeID)) return NULL;
    CFUUIDRef factoryID = CFUUIDCreateFromString(kCFAllocatorDefault, CFSTR("ECA38A44-7F4B-44B2-B8D2-7D696D9F1B87"));
    CFPlugInAddInstanceForFactory(factoryID);
    gWrapper.factoryID = factoryID;
    return &gWrapper;
}

#pragma clang diagnostic pop
