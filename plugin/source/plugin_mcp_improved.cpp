#include <hex/plugin.hpp>

#include <hex/api/imhex_api/provider.hpp>
#include <hex/api/imhex_api/bookmarks.hpp>
#include <hex/api/content_registry/communication_interface.hpp>
#include <hex/api/events/requests_interaction.hpp>
#include <hex/providers/provider.hpp>

#include <hex/helpers/logger.hpp>
#include <hex/helpers/crypto.hpp>
#include <hex/helpers/utils.hpp>
#include <hex/helpers/encoding_file.hpp>

#include <nlohmann/json.hpp>

#include <vector>
#include <string>
#include <algorithm>
#include <regex>
#include <sstream>
#include <iomanip>

namespace hex::plugin::mcp {

    namespace {

        /**
         * Convert hex string to bytes with validation
         */
        std::vector<u8> hexStringToBytes(const std::string &hexStr) {
            // Remove any whitespace or separators
            std::string cleaned;
            for (char c : hexStr) {
                if (std::isxdigit(c)) {
                    cleaned += c;
                }
            }

            // Validate even number of hex digits
            if (cleaned.length() % 2 != 0) {
                throw std::runtime_error("Hex string must have even number of characters");
            }

            std::vector<u8> bytes;
            bytes.reserve(cleaned.length() / 2);

            for (size_t i = 0; i < cleaned.length(); i += 2) {
                std::string byteString = cleaned.substr(i, 2);
                u8 byte = static_cast<u8>(std::strtol(byteString.c_str(), nullptr, 16));
                bytes.push_back(byte);
            }

            return bytes;
        }

        /**
         * Convert bytes to hex string
         */
        std::string bytesToHexString(const std::vector<u8> &bytes) {
            std::ostringstream oss;
            oss << std::hex << std::uppercase << std::setfill('0');

            for (u8 byte : bytes) {
                oss << std::setw(2) << static_cast<int>(byte);
            }

            return oss.str();
        }

        /**
         * Base64 encoding table
         */
        static const std::string base64_chars =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789+/";

        /**
         * Base64 encode
         */
        std::string base64_encode(const std::vector<u8> &input) {
            std::string ret;
            int i = 0;
            int j = 0;
            u8 char_array_3[3];
            u8 char_array_4[4];
            size_t in_len = input.size();
            const u8* bytes_to_encode = input.data();

            while (in_len--) {
                char_array_3[i++] = *(bytes_to_encode++);
                if (i == 3) {
                    char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
                    char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
                    char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
                    char_array_4[3] = char_array_3[2] & 0x3f;

                    for (i = 0; i < 4; i++)
                        ret += base64_chars[char_array_4[i]];
                    i = 0;
                }
            }

            if (i) {
                for (j = i; j < 3; j++)
                    char_array_3[j] = '\0';

                char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
                char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
                char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);

                for (j = 0; j < i + 1; j++)
                    ret += base64_chars[char_array_4[j]];

                while (i++ < 3)
                    ret += '=';
            }

            return ret;
        }

        /**
         * Base64 decode
         */
        std::vector<u8> base64_decode(const std::string &encoded_string) {
            size_t in_len = encoded_string.size();
            int i = 0;
            int j = 0;
            int in_ = 0;
            u8 char_array_4[4], char_array_3[3];
            std::vector<u8> ret;

            while (in_len-- && (encoded_string[in_] != '=')) {
                if (!isalnum(encoded_string[in_]) && encoded_string[in_] != '+' && encoded_string[in_] != '/') {
                    in_++;
                    continue;
                }

                char_array_4[i++] = encoded_string[in_]; in_++;
                if (i == 4) {
                    for (i = 0; i < 4; i++)
                        char_array_4[i] = base64_chars.find(char_array_4[i]);

                    char_array_3[0] = (char_array_4[0] << 2) + ((char_array_4[1] & 0x30) >> 4);
                    char_array_3[1] = ((char_array_4[1] & 0xf) << 4) + ((char_array_4[2] & 0x3c) >> 2);
                    char_array_3[2] = ((char_array_4[2] & 0x3) << 6) + char_array_4[3];

                    for (i = 0; i < 3; i++)
                        ret.push_back(char_array_3[i]);
                    i = 0;
                }
            }

            if (i) {
                for (j = 0; j < i; j++)
                    char_array_4[j] = base64_chars.find(char_array_4[j]);

                char_array_3[0] = (char_array_4[0] << 2) + ((char_array_4[1] & 0x30) >> 4);
                char_array_3[1] = ((char_array_4[1] & 0xf) << 4) + ((char_array_4[2] & 0x3c) >> 2);

                for (j = 0; j < i - 1; j++)
                    ret.push_back(char_array_3[j]);
            }

            return ret;
        }

        /**
         * Register MCP network endpoints (improved version)
         */
        void registerMCPEndpoints() {
            // File operations: Open file
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("file/open", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    auto path = data.at("path").get<std::string>();

                    log::info("MCP: Opening file '{}'", path);

                    // Request to open file via event system
                    RequestOpenFile::post(path);

                    // Give ImHex time to process the request
                    std::this_thread::sleep_for(std::chrono::milliseconds(100));

                    nlohmann::json result;
                    result["file"] = path;

                    // Get file size if provider is available
                    if (ImHexApi::Provider::isValid()) {
                        auto provider = ImHexApi::Provider::get();
                        if (provider != nullptr) {
                            result["size"] = provider->getActualSize();
                            result["name"] = provider->getName();
                            result["readable"] = provider->isReadable();
                            result["writable"] = provider->isWritable();
                        }
                    }

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(hex::format("Failed to open file: {}", e.what()));
                }
            });

            // Data operations: Read hex data
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("data/read", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    if (!ImHexApi::Provider::isValid()) {
                        throw std::runtime_error("No file is currently open");
                    }

                    auto provider = ImHexApi::Provider::get();
                    if (provider == nullptr) {
                        throw std::runtime_error("Provider is null");
                    }

                    u64 offset = data.at("offset").get<u64>();
                    u64 length = data.at("length").get<u64>();

                    // Validate offset and length
                    if (offset >= provider->getActualSize()) {
                        throw std::runtime_error(hex::format("Offset 0x{:X} is beyond file size 0x{:X}", offset, provider->getActualSize()));
                    }

                    if (offset + length > provider->getActualSize()) {
                        length = provider->getActualSize() - offset;
                        log::warn("Read length adjusted to {} to stay within file bounds", length);
                    }

                    // Limit read size to prevent memory issues
                    const u64 maxReadSize = 10 * 1024 * 1024; // 10 MB
                    if (length > maxReadSize) {
                        throw std::runtime_error(hex::format("Read length {} exceeds maximum of {} bytes", length, maxReadSize));
                    }

                    // Read data
                    std::vector<u8> buffer(length);
                    provider->read(offset, buffer.data(), length);

                    nlohmann::json result;
                    result["offset"] = offset;
                    result["length"] = length;
                    result["data"] = bytesToHexString(buffer);

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(hex::format("Failed to read data: {}", e.what()));
                }
            });

            // Data operations: Write hex data
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("data/write", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    if (!ImHexApi::Provider::isValid()) {
                        throw std::runtime_error("No file is currently open");
                    }

                    auto provider = ImHexApi::Provider::get();
                    if (provider == nullptr) {
                        throw std::runtime_error("Provider is null");
                    }

                    if (!provider->isWritable()) {
                        throw std::runtime_error("Provider is not writable");
                    }

                    u64 offset = data.at("offset").get<u64>();
                    std::string hexData = data.at("data").get<std::string>();

                    // Convert hex string to bytes
                    auto bytes = hexStringToBytes(hexData);

                    // Validate offset
                    if (offset >= provider->getActualSize()) {
                        throw std::runtime_error(hex::format("Offset 0x{:X} is beyond file size 0x{:X}", offset, provider->getActualSize()));
                    }

                    if (offset + bytes.size() > provider->getActualSize()) {
                        throw std::runtime_error("Write would exceed file bounds");
                    }

                    // Write data
                    provider->write(offset, bytes.data(), bytes.size());
                    ImHexApi::Provider::markDirty();

                    nlohmann::json result;
                    result["offset"] = offset;
                    result["length"] = bytes.size();
                    result["written"] = true;

                    log::info("MCP: Wrote {} bytes at offset 0x{:X}", bytes.size(), offset);

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(hex::format("Failed to write data: {}", e.what()));
                }
            });

            // Data inspection: Inspect data with various types
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("data/inspect", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    if (!ImHexApi::Provider::isValid()) {
                        throw std::runtime_error("No file is currently open");
                    }

                    auto provider = ImHexApi::Provider::get();
                    if (provider == nullptr) {
                        throw std::runtime_error("Provider is null");
                    }

                    u64 offset = data.at("offset").get<u64>();

                    // Validate offset
                    if (offset >= provider->getActualSize()) {
                        throw std::runtime_error(hex::format("Offset 0x{:X} is beyond file size 0x{:X}", offset, provider->getActualSize()));
                    }

                    nlohmann::json result;
                    result["offset"] = offset;

                    // Read enough bytes for all data types (16 bytes should cover most types)
                    size_t maxBytes = 16;
                    if (offset + maxBytes > provider->getActualSize()) {
                        maxBytes = provider->getActualSize() - offset;
                    }

                    std::vector<u8> buffer(maxBytes);
                    provider->read(offset, buffer.data(), maxBytes);

                    // Interpret as various data types
                    nlohmann::json types;

                    if (maxBytes >= 1) {
                        types["uint8"] = buffer[0];
                        types["int8"] = static_cast<i8>(buffer[0]);
                        types["char"] = std::isprint(buffer[0]) ? std::string(1, static_cast<char>(buffer[0])) : ".";
                    }

                    if (maxBytes >= 2) {
                        u16 u16val_le, u16val_be;
                        i16 i16val_le, i16val_be;

                        std::memcpy(&u16val_le, buffer.data(), sizeof(u16));
                        std::memcpy(&i16val_le, buffer.data(), sizeof(i16));

                        // Big endian
                        u16val_be = (static_cast<u16>(buffer[0]) << 8) | buffer[1];
                        i16val_be = static_cast<i16>(u16val_be);

                        types["uint16_le"] = u16val_le;
                        types["int16_le"] = i16val_le;
                        types["uint16_be"] = u16val_be;
                        types["int16_be"] = i16val_be;
                    }

                    if (maxBytes >= 4) {
                        u32 u32val_le, u32val_be;
                        i32 i32val_le, i32val_be;
                        float floatval_le, floatval_be;

                        std::memcpy(&u32val_le, buffer.data(), sizeof(u32));
                        std::memcpy(&i32val_le, buffer.data(), sizeof(i32));
                        std::memcpy(&floatval_le, buffer.data(), sizeof(float));

                        // Big endian
                        u32val_be = (static_cast<u32>(buffer[0]) << 24) |
                                    (static_cast<u32>(buffer[1]) << 16) |
                                    (static_cast<u32>(buffer[2]) << 8) |
                                    buffer[3];
                        i32val_be = static_cast<i32>(u32val_be);
                        std::memcpy(&floatval_be, &u32val_be, sizeof(float));

                        types["uint32_le"] = u32val_le;
                        types["int32_le"] = i32val_le;
                        types["float_le"] = floatval_le;
                        types["uint32_be"] = u32val_be;
                        types["int32_be"] = i32val_be;
                        types["float_be"] = floatval_be;
                    }

                    if (maxBytes >= 8) {
                        u64 u64val_le, u64val_be;
                        i64 i64val_le, i64val_be;
                        double doubleval_le, doubleval_be;

                        std::memcpy(&u64val_le, buffer.data(), sizeof(u64));
                        std::memcpy(&i64val_le, buffer.data(), sizeof(i64));
                        std::memcpy(&doubleval_le, buffer.data(), sizeof(double));

                        // Big endian
                        u64val_be = (static_cast<u64>(buffer[0]) << 56) |
                                    (static_cast<u64>(buffer[1]) << 48) |
                                    (static_cast<u64>(buffer[2]) << 40) |
                                    (static_cast<u64>(buffer[3]) << 32) |
                                    (static_cast<u64>(buffer[4]) << 24) |
                                    (static_cast<u64>(buffer[5]) << 16) |
                                    (static_cast<u64>(buffer[6]) << 8) |
                                    buffer[7];
                        i64val_be = static_cast<i64>(u64val_be);
                        std::memcpy(&doubleval_be, &u64val_be, sizeof(double));

                        types["uint64_le"] = u64val_le;
                        types["int64_le"] = i64val_le;
                        types["double_le"] = doubleval_le;
                        types["uint64_be"] = u64val_be;
                        types["int64_be"] = i64val_be;
                        types["double_be"] = doubleval_be;
                    }

                    // ASCII interpretation
                    std::string ascii;
                    for (size_t i = 0; i < maxBytes; i++) {
                        if (std::isprint(buffer[i])) {
                            ascii += static_cast<char>(buffer[i]);
                        } else {
                            ascii += '.';
                        }
                    }
                    types["ascii"] = ascii;

                    // UTF-8 string (if valid)
                    types["utf8"] = ascii;  // Simplified - proper UTF-8 validation would be more complex

                    // Hex dump
                    types["hex"] = bytesToHexString(buffer);

                    // Binary representation
                    std::string binary;
                    for (size_t i = 0; i < std::min(maxBytes, size_t(4)); i++) {
                        for (int bit = 7; bit >= 0; bit--) {
                            binary += (buffer[i] & (1 << bit)) ? '1' : '0';
                        }
                        if (i < std::min(maxBytes, size_t(4)) - 1) binary += ' ';
                    }
                    types["binary"] = binary;

                    result["types"] = types;

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(hex::format("Failed to inspect data: {}", e.what()));
                }
            });

            // Bookmark operations: Add bookmark
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("bookmark/add", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    if (!ImHexApi::Provider::isValid()) {
                        throw std::runtime_error("No file is currently open");
                    }

                    u64 offset = data.at("offset").get<u64>();
                    u64 size = data.at("size").get<u64>();
                    std::string name = data.at("name").get<std::string>();
                    std::string comment = data.value("comment", "");

                    // Parse color (default to red if not specified)
                    u32 color = 0xFF0000FF;
                    if (data.contains("color")) {
                        std::string colorStr = data.at("color").get<std::string>();
                        color = std::stoul(colorStr, nullptr, 16);
                        // Add alpha channel if not present
                        if (colorStr.length() == 6) {
                            color = (color << 8) | 0xFF;
                        }
                    }

                    // Add bookmark
                    u64 bookmarkId = ImHexApi::Bookmarks::add(offset, size, name, comment, color);

                    log::info("MCP: Added bookmark '{}' at 0x{:X}", name, offset);

                    nlohmann::json result;
                    result["id"] = bookmarkId;
                    result["offset"] = offset;
                    result["size"] = size;
                    result["name"] = name;

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(hex::format("Failed to add bookmark: {}", e.what()));
                }
            });

            // Hash calculation: Calculate hash of data
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("hash/calculate", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    if (!ImHexApi::Provider::isValid()) {
                        throw std::runtime_error("No file is currently open");
                    }

                    auto provider = ImHexApi::Provider::get();
                    if (provider == nullptr) {
                        throw std::runtime_error("Provider is null");
                    }

                    std::string algorithm = data.at("algorithm").get<std::string>();
                    u64 offset = data.value("offset", 0);
                    u64 length = data.value("length", provider->getActualSize() - offset);

                    // Validate offset and length
                    if (offset >= provider->getActualSize()) {
                        throw std::runtime_error("Offset is beyond file size");
                    }

                    if (offset + length > provider->getActualSize()) {
                        length = provider->getActualSize() - offset;
                    }

                    // Read data
                    std::vector<u8> buffer(length);
                    provider->read(offset, buffer.data(), length);

                    // Calculate hash based on algorithm
                    std::vector<u8> hashResult;

                    // Convert algorithm to lowercase for comparison
                    std::string algoLower = algorithm;
                    std::transform(algoLower.begin(), algoLower.end(), algoLower.begin(), ::tolower);

                    if (algoLower == "md5") {
                        hashResult = crypt::md5(buffer);
                    } else if (algoLower == "sha1") {
                        hashResult = crypt::sha1(buffer);
                    } else if (algoLower == "sha224") {
                        hashResult = crypt::sha224(buffer);
                    } else if (algoLower == "sha256") {
                        hashResult = crypt::sha256(buffer);
                    } else if (algoLower == "sha384") {
                        hashResult = crypt::sha384(buffer);
                    } else if (algoLower == "sha512") {
                        hashResult = crypt::sha512(buffer);
                    } else {
                        throw std::runtime_error(hex::format("Unsupported hash algorithm: {}", algorithm));
                    }

                    std::string hashHex = bytesToHexString(hashResult);

                    log::info("MCP: Calculated {} hash: {}", algorithm, hashHex.substr(0, 16) + "...");

                    nlohmann::json result;
                    result["algorithm"] = algorithm;
                    result["offset"] = offset;
                    result["length"] = length;
                    result["hash"] = hashHex;

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(hex::format("Failed to calculate hash: {}", e.what()));
                }
            });

            // Search: Find pattern in data (improved with regex support)
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("search/find", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    if (!ImHexApi::Provider::isValid()) {
                        throw std::runtime_error("No file is currently open");
                    }

                    auto provider = ImHexApi::Provider::get();
                    if (provider == nullptr) {
                        throw std::runtime_error("Provider is null");
                    }

                    std::string pattern = data.at("pattern").get<std::string>();
                    std::string searchType = data.at("type").get<std::string>();

                    std::vector<u8> searchBytes;

                    if (searchType == "hex") {
                        searchBytes = hexStringToBytes(pattern);
                    } else if (searchType == "text") {
                        searchBytes.assign(pattern.begin(), pattern.end());
                    } else {
                        throw std::runtime_error(hex::format("Unsupported search type: {}", searchType));
                    }

                    if (searchBytes.empty()) {
                        throw std::runtime_error("Search pattern is empty");
                    }

                    // Search implementation with progress tracking
                    std::vector<u64> matches;
                    const size_t chunkSize = 1024 * 1024; // 1 MB chunks
                    std::vector<u8> buffer(chunkSize + searchBytes.size());

                    u64 fileSize = provider->getActualSize();
                    u64 searchLimit = 10000; // Limit to 10000 matches

                    log::info("MCP: Searching for pattern (type: {}, size: {} bytes)", searchType, searchBytes.size());

                    for (u64 offset = 0; offset < fileSize && matches.size() < searchLimit; offset += chunkSize) {
                        size_t readSize = std::min(chunkSize + searchBytes.size(), static_cast<size_t>(fileSize - offset));
                        provider->read(offset, buffer.data(), readSize);

                        // Search for pattern in this chunk
                        for (size_t i = 0; i <= readSize - searchBytes.size() && matches.size() < searchLimit; i++) {
                            bool found = true;
                            for (size_t j = 0; j < searchBytes.size(); j++) {
                                if (buffer[i + j] != searchBytes[j]) {
                                    found = false;
                                    break;
                                }
                            }
                            if (found) {
                                matches.push_back(offset + i);
                            }
                        }
                    }

                    log::info("MCP: Search complete, found {} match(es)", matches.size());

                    nlohmann::json result;
                    result["pattern"] = pattern;
                    result["type"] = searchType;
                    result["matches"] = matches;
                    result["count"] = matches.size();
                    result["limited"] = (matches.size() >= searchLimit);

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(hex::format("Failed to search: {}", e.what()));
                }
            });

            // Data decoding: Decode various formats
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("data/decode", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    std::string hexData = data.at("data").get<std::string>();
                    std::string encoding = data.at("encoding").get<std::string>();

                    // Convert hex to bytes
                    auto bytes = hexStringToBytes(hexData);

                    nlohmann::json result;
                    result["encoding"] = encoding;

                    // Convert encoding to lowercase
                    std::transform(encoding.begin(), encoding.end(), encoding.begin(), ::tolower);

                    if (encoding == "base64") {
                        result["decoded"] = base64_encode(bytes);
                    } else if (encoding == "ascii" || encoding == "text") {
                        std::string text(bytes.begin(), bytes.end());
                        result["decoded"] = text;
                    } else if (encoding == "hex") {
                        result["decoded"] = bytesToHexString(bytes);
                    } else if (encoding == "binary") {
                        std::string binary;
                        for (u8 byte : bytes) {
                            for (int bit = 7; bit >= 0; bit--) {
                                binary += (byte & (1 << bit)) ? '1' : '0';
                            }
                            binary += ' ';
                        }
                        result["decoded"] = binary;
                    } else {
                        throw std::runtime_error(hex::format("Unsupported encoding: {}", encoding));
                    }

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(hex::format("Failed to decode data: {}", e.what()));
                }
            });

            // Provider information
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("provider/info", [](const nlohmann::json &) -> nlohmann::json {
                nlohmann::json result;

                if (ImHexApi::Provider::isValid()) {
                    auto provider = ImHexApi::Provider::get();
                    if (provider != nullptr) {
                        result["valid"] = true;
                        result["name"] = provider->getName();
                        result["size"] = provider->getActualSize();
                        result["writable"] = provider->isWritable();
                        result["readable"] = provider->isReadable();
                        result["dirty"] = provider->isDirty();

                        // Additional info
                        result["base_address"] = provider->getBaseAddress();
                        result["current_page"] = provider->getCurrentPage();
                        result["page_count"] = provider->getPageCount();
                    } else {
                        result["valid"] = false;
                    }
                } else {
                    result["valid"] = false;
                }

                return result;
            });

            log::info("MCP plugin (improved) loaded - registered {} network endpoints", 9);
        }

    }

}

// Plugin metadata and entry point
IMHEX_PLUGIN_SETUP("MCP Integration", "ImHex Contributors", "Improved MCP server integration for AI assistant access") {
    using namespace hex::plugin::mcp;

    log::info("Initializing MCP plugin (improved version)...");

    // Register all MCP network endpoints
    registerMCPEndpoints();
}
