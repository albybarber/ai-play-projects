#pragma once
#import <CoreMediaIO/CMIOHardwarePlugIn.h>
#import <Foundation/Foundation.h>
#import "VOCDevice.h"

// Singleton plugin object
@interface VOCPlugIn : NSObject

@property (nonatomic, assign) CMIOObjectID objectID;
@property (nonatomic, strong) VOCDevice *device;

+ (VOCPlugIn *)shared;

- (void)initializeWithObjectID:(CMIOObjectID)objectID;

@end

// C factory function declared in Info.plist
#ifdef __cplusplus
extern "C" {
#endif
void *VOCPlugInFactory(CFAllocatorRef allocator, CFUUIDRef requestedTypeUUID);
#ifdef __cplusplus
}
#endif
