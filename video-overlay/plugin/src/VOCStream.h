#pragma once
#import <CoreMediaIO/CMIOHardwarePlugIn.h>
#import <CoreMedia/CoreMedia.h>
#import <CoreVideo/CoreVideo.h>
#import <Foundation/Foundation.h>

@interface VOCStream : NSObject

@property (nonatomic, assign) CMIOObjectID objectID;
@property (nonatomic, assign) CMIOObjectID deviceID;

// Queue provided to the host — frames are posted here
@property (nonatomic, assign) CMSimpleQueueRef queue;

// Callback invoked after enqueuing a frame
@property (nonatomic, assign) CMIODeviceStreamQueueAlteredProc alteredProc;
@property (nonatomic, assign) void *alteredRefCon;

@property (nonatomic, strong) dispatch_queue_t frameQueue;
@property (nonatomic, strong) dispatch_source_t frameTimer;

- (instancetype)initWithObjectID:(CMIOObjectID)objectID deviceID:(CMIOObjectID)deviceID;
- (void)startFrameDelivery;
- (void)stopFrameDelivery;
- (Boolean)hasProperty:(CMIOObjectPropertyAddress const *)address;
- (OSStatus)getPropertyDataSize:(CMIOObjectPropertyAddress const *)address
              qualifierDataSize:(UInt32)qualDataSize
                  qualifierData:(const void *)qualData
                          size:(UInt32 *)outSize;
- (OSStatus)getPropertyData:(CMIOObjectPropertyAddress const *)address
          qualifierDataSize:(UInt32)qualDataSize
              qualifierData:(const void *)qualData
                   dataSize:(UInt32)dataSize
               bytesWritten:(UInt32 *)outBytesWritten
                       data:(void *)outData;

@end
