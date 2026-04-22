#pragma once
#import <CoreMediaIO/CMIOHardwarePlugIn.h>
#import <Foundation/Foundation.h>
#import "VOCStream.h"

@interface VOCDevice : NSObject

@property (nonatomic, assign) CMIOObjectID objectID;
@property (nonatomic, strong) VOCStream *stream;

- (instancetype)initWithObjectID:(CMIOObjectID)objectID streamID:(CMIOObjectID)streamID;
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
