// Example ImHex Pattern Language scripts for use with the MCP server

// 1. Simple PE (Portable Executable) Header
struct DOSHeader {
    char magic[2];          // "MZ"
    u16 lastsize;
    u16 nblocks;
    u16 nreloc;
    u16 hdrsize;
    u16 minalloc;
    u16 maxalloc;
    u16 ss;
    u16 sp;
    u16 checksum;
    u16 ip;
    u16 cs;
    u16 relocpos;
    u16 noverlay;
    u16 reserved1[4];
    u16 oem_id;
    u16 oem_info;
    u16 reserved2[10];
    u32 e_lfanew;          // Offset to PE header
};

struct PEHeader {
    char signature[4];      // "PE\0\0"
    u16 machine;
    u16 numberOfSections;
    u32 timeDateStamp;
    u32 pointerToSymbolTable;
    u32 numberOfSymbols;
    u16 sizeOfOptionalHeader;
    u16 characteristics;
};

// 2. ELF (Executable and Linkable Format) Header
struct ELFHeader {
    char magic[4];          // "\x7FELF"
    u8 class;              // 1 = 32-bit, 2 = 64-bit
    u8 data;               // 1 = little endian, 2 = big endian
    u8 version;
    u8 osabi;
    u8 abiversion;
    u8 pad[7];
    u16 type;
    u16 machine;
    u32 version2;
    u64 entry;
    u64 phoff;
    u64 shoff;
    u32 flags;
    u16 ehsize;
    u16 phentsize;
    u16 phnum;
    u16 shentsize;
    u16 shnum;
    u16 shstrndx;
};

// 3. ZIP Archive
struct ZIPLocalFileHeader {
    u32 signature;          // 0x04034b50
    u16 version;
    u16 flags;
    u16 compression;
    u16 modTime;
    u16 modDate;
    u32 crc32;
    u32 compressedSize;
    u32 uncompressedSize;
    u16 filenameLength;
    u16 extraFieldLength;
    char filename[filenameLength];
    u8 extraField[extraFieldLength];
};

// 4. PNG Image Format
struct PNGChunk {
    u32 length;
    char type[4];
    u8 data[length];
    u32 crc;
};

struct PNGHeader {
    u8 signature[8];        // 0x89 0x50 0x4E 0x47 0x0D 0x0A 0x1A 0x0A
    PNGChunk chunks[while($ < sizeof($))];
};

// 5. BMP Image Format
struct BMPHeader {
    char signature[2];      // "BM"
    u32 fileSize;
    u16 reserved1;
    u16 reserved2;
    u32 dataOffset;
    u32 headerSize;
    s32 width;
    s32 height;
    u16 planes;
    u16 bitsPerPixel;
    u32 compression;
    u32 imageSize;
    s32 xPixelsPerMeter;
    s32 yPixelsPerMeter;
    u32 colorsUsed;
    u32 colorsImportant;
};

// Example usage: Place the appropriate struct at offset 0
// DOSHeader dosHeader @ 0x00;
// ELFHeader elfHeader @ 0x00;
// ZIPLocalFileHeader zipHeader @ 0x00;
// PNGHeader pngHeader @ 0x00;
// BMPHeader bmpHeader @ 0x00;
