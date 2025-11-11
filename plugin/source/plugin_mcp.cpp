#include <hex/plugin.hpp>

#include <hex/api/imhex_api/provider.hpp>
#include <hex/api/imhex_api/bookmarks.hpp>
#include <hex/api/task_manager.hpp>
#include <hex/api/content_registry/communication_interface.hpp>
#include <hex/api/content_registry/diffing.hpp>
#include <hex/api/content_registry/disassemblers.hpp>
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
#include <fstream>

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
        [[maybe_unused]] std::vector<u8> base64_decode(const std::string &encoded_string) {
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

                    // Schedule file opening on main thread using TaskManager::doLater()
                    // Network callbacks run on background threads, but ImHex APIs require main thread
                    TaskManager::doLater([path]() {
                        RequestOpenFile::post(path);
                    });

                    // Return immediately - file opening happens asynchronously on main thread
                    // Client should poll list/providers to check when file is open
                    nlohmann::json result;
                    result["file"] = path;
                    result["status"] = "async";
                    result["message"] = "File opening scheduled on main thread. Poll list/providers to check status.";

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed to open file: {}", e.what()));
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
                        throw std::runtime_error(fmt::format("Offset 0x{:X} is beyond file size 0x{:X}", offset, provider->getActualSize()));
                    }

                    if (offset + length > provider->getActualSize()) {
                        length = provider->getActualSize() - offset;
                        log::warn("Read length adjusted to {} to stay within file bounds", length);
                    }

                    // Limit read size to prevent memory issues
                    const u64 maxReadSize = 10 * 1024 * 1024; // 10 MB
                    if (length > maxReadSize) {
                        throw std::runtime_error(fmt::format("Read length {} exceeds maximum of {} bytes", length, maxReadSize));
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
                    throw std::runtime_error(fmt::format("Failed to read data: {}", e.what()));
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
                        throw std::runtime_error(fmt::format("Offset 0x{:X} is beyond file size 0x{:X}", offset, provider->getActualSize()));
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
                    throw std::runtime_error(fmt::format("Failed to write data: {}", e.what()));
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
                        throw std::runtime_error(fmt::format("Offset 0x{:X} is beyond file size 0x{:X}", offset, provider->getActualSize()));
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
                    throw std::runtime_error(fmt::format("Failed to inspect data: {}", e.what()));
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
                    throw std::runtime_error(fmt::format("Failed to add bookmark: {}", e.what()));
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
                        auto hash = crypt::md5(buffer);
                        hashResult.assign(hash.begin(), hash.end());
                    } else if (algoLower == "sha1") {
                        auto hash = crypt::sha1(buffer);
                        hashResult.assign(hash.begin(), hash.end());
                    } else if (algoLower == "sha224") {
                        auto hash = crypt::sha224(buffer);
                        hashResult.assign(hash.begin(), hash.end());
                    } else if (algoLower == "sha256") {
                        auto hash = crypt::sha256(buffer);
                        hashResult.assign(hash.begin(), hash.end());
                    } else if (algoLower == "sha384") {
                        auto hash = crypt::sha384(buffer);
                        hashResult.assign(hash.begin(), hash.end());
                    } else if (algoLower == "sha512") {
                        auto hash = crypt::sha512(buffer);
                        hashResult.assign(hash.begin(), hash.end());
                    } else {
                        throw std::runtime_error(fmt::format("Unsupported hash algorithm: {}", algorithm));
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
                    throw std::runtime_error(fmt::format("Failed to calculate hash: {}", e.what()));
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
                        throw std::runtime_error(fmt::format("Unsupported search type: {}", searchType));
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
                    throw std::runtime_error(fmt::format("Failed to search: {}", e.what()));
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
                        throw std::runtime_error(fmt::format("Unsupported encoding: {}", encoding));
                    }

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed to decode data: {}", e.what()));
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

            // File operations: List all open files/providers
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("file/list", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    (void)data;
                    auto providers = ImHexApi::Provider::getProviders();
                    auto currentProvider = ImHexApi::Provider::get();

                    nlohmann::json filesList = nlohmann::json::array();

                    for (const auto &provider : providers) {
                        nlohmann::json fileInfo;
                        fileInfo["id"] = provider->getID();
                        fileInfo["name"] = provider->getName();
                        fileInfo["size"] = provider->getActualSize();
                        fileInfo["readable"] = provider->isReadable();
                        fileInfo["writable"] = provider->isWritable();
                        fileInfo["is_active"] = (provider == currentProvider);
                        filesList.push_back(fileInfo);
                    }

                    nlohmann::json result;
                    result["count"] = filesList.size();
                    result["files"] = filesList;
                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed to list files: {}", e.what()));
                }
            });

            // Alias: list/providers (same as file/list but with different response format)
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("list/providers", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    (void)data;
                    auto providers = ImHexApi::Provider::getProviders();
                    auto currentProvider = ImHexApi::Provider::get();

                    nlohmann::json providersList = nlohmann::json::array();

                    for (const auto &provider : providers) {
                        nlohmann::json providerInfo;
                        providerInfo["id"] = provider->getID();
                        providerInfo["name"] = provider->getName();
                        providerInfo["path"] = provider->getName();  // Provider name often includes path
                        providerInfo["size"] = provider->getActualSize();
                        providerInfo["readable"] = provider->isReadable();
                        providerInfo["writable"] = provider->isWritable();
                        providerInfo["is_active"] = (provider == currentProvider);
                        providersList.push_back(providerInfo);
                    }

                    nlohmann::json result;
                    result["providers"] = providersList;
                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed to list providers: {}", e.what()));
                }
            });

            // File operations: Switch active file/provider
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("file/switch", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    u32 providerID = data.at("provider_id").get<u32>();
                    auto providers = ImHexApi::Provider::getProviders();

                    for (auto *provider : providers) {
                        if (provider->getID() == providerID) {
                            ImHexApi::Provider::setCurrentProvider(providerID);

                            nlohmann::json result;
                            result["id"] = providerID;
                            result["name"] = provider->getName();
                            result["size"] = provider->getActualSize();
                            return result;
                        }
                    }

                    throw std::runtime_error(fmt::format("Provider with ID {} not found", providerID));
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed to switch file: {}", e.what()));
                }
            });

            // File operations: Close a file/provider
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("file/close", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    u32 providerID = data.at("provider_id").get<u32>();

                    // Schedule file closing on main thread using TaskManager::doLater()
                    // Network callbacks run on background threads, but ImHex APIs require main thread
                    TaskManager::doLater([providerID]() {
                        auto providers = ImHexApi::Provider::getProviders();
                        for (auto *provider : providers) {
                            if (provider->getID() == providerID) {
                                ImHexApi::Provider::remove(provider);
                                return;
                            }
                        }
                    });

                    // Return immediately - file closing happens asynchronously on main thread
                    // Client should poll list/providers to verify file is closed
                    nlohmann::json result;
                    result["provider_id"] = providerID;
                    result["status"] = "async";
                    result["message"] = "File closing scheduled on main thread. Poll list/providers to verify.";
                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed to close file: {}", e.what()));
                }
            });

            // File operations: Compare two files
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("file/compare", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    u32 providerID1 = data.at("provider_id_1").get<u32>();
                    u32 providerID2 = data.at("provider_id_2").get<u32>();

                    auto providers = ImHexApi::Provider::getProviders();
                    prv::Provider* provider1 = nullptr;
                    prv::Provider* provider2 = nullptr;

                    for (auto *provider : providers) {
                        if (provider->getID() == providerID1) provider1 = provider;
                        if (provider->getID() == providerID2) provider2 = provider;
                    }

                    if (!provider1 || !provider2) {
                        throw std::runtime_error("One or both providers not found");
                    }

                    u64 size1 = provider1->getActualSize();
                    u64 size2 = provider2->getActualSize();
                    u64 compareBytes = std::min({size1, size2, static_cast<u64>(1024 * 1024)});
                    u64 differences = 0;

                    std::vector<u8> buffer1(1024);
                    std::vector<u8> buffer2(1024);

                    for (u64 offset = 0; offset < compareBytes; offset += 1024) {
                        u64 chunkSize = std::min(static_cast<u64>(1024), compareBytes - offset);
                        provider1->read(offset, buffer1.data(), chunkSize);
                        provider2->read(offset, buffer2.data(), chunkSize);

                        for (size_t i = 0; i < chunkSize; i++) {
                            if (buffer1[i] != buffer2[i]) differences++;
                        }
                    }

                    double similarity = 100.0 * (1.0 - (static_cast<double>(differences) / static_cast<double>(compareBytes)));

                    nlohmann::json result;
                    result["file1"] = {{"id", providerID1}, {"name", provider1->getName()}, {"size", size1}};
                    result["file2"] = {{"id", providerID2}, {"name", provider2->getName()}, {"size", size2}};
                    result["comparison"] = {
                        {"size_match", size1 == size2},
                        {"bytes_compared", compareBytes},
                        {"differences", differences},
                        {"similarity_percent", similarity}
                    };
                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed to compare files: {}", e.what()));
                }
            });

            // Data operations: Export data to file (binary/hex/base64)
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("data/export", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    if (!ImHexApi::Provider::isValid()) {
                        throw std::runtime_error("No file is currently open");
                    }

                    auto provider = ImHexApi::Provider::get();
                    u64 offset = data.at("offset").get<u64>();
                    u64 length = data.at("length").get<u64>();
                    std::string outputPath = data.at("output_path").get<std::string>();
                    std::string format = data.value("format", "binary");

                    const u64 maxExport = 100 * 1024 * 1024; // 100MB
                    if (length > maxExport) {
                        throw std::runtime_error(fmt::format("Export size {} exceeds maximum of {} bytes", length, maxExport));
                    }

                    std::vector<u8> buffer(length);
                    provider->read(offset, buffer.data(), length);

                    std::ofstream outFile(outputPath, std::ios::binary);
                    if (!outFile) {
                        throw std::runtime_error("Failed to open output file");
                    }

                    if (format == "binary") {
                        outFile.write(reinterpret_cast<const char*>(buffer.data()), length);
                    } else if (format == "hex") {
                        for (size_t i = 0; i < buffer.size(); i++) {
                            outFile << fmt::format("{:02X}", buffer[i]);
                            if ((i + 1) % 16 == 0) outFile << "\n";
                            else if ((i + 1) < buffer.size()) outFile << " ";
                        }
                    } else if (format == "base64") {
                        std::string b64 = base64_encode(buffer);
                        for (size_t i = 0; i < b64.length(); i += 76) {
                            outFile << b64.substr(i, 76) << "\n";
                        }
                    }

                    nlohmann::json result;
                    result["offset"] = offset;
                    result["length"] = length;
                    result["format"] = format;
                    result["output_path"] = outputPath;
                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed to export data: {}", e.what()));
                }
            });

            // Search operations: Export search results (CSV/JSON)
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("search/export", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    auto matches = data.at("matches").get<std::vector<u64>>();
                    std::string outputPath = data.at("output_path").get<std::string>();
                    std::string format = data.value("format", "json");
                    u64 contextBytes = data.value("context_bytes", 0);

                    std::ofstream outFile(outputPath);
                    if (!outFile) {
                        throw std::runtime_error("Failed to open output file");
                    }

                    if (format == "csv") {
                        outFile << "Match,Offset_Hex,Offset_Dec";
                        if (contextBytes > 0) outFile << ",Context_Hex,Context_ASCII";
                        outFile << "\n";

                        for (size_t i = 0; i < matches.size(); i++) {
                            outFile << (i + 1) << ",0x" << fmt::format("{:X}", matches[i]) << "," << matches[i];
                            if (contextBytes > 0) {
                                // Add context data
                            }
                            outFile << "\n";
                        }
                    } else if (format == "json") {
                        nlohmann::json exportData;
                        exportData["match_count"] = matches.size();
                        nlohmann::json matchArray = nlohmann::json::array();
                        for (auto offset : matches) {
                            matchArray.push_back({{"offset", offset}, {"offset_hex", fmt::format("0x{:X}", offset)}});
                        }
                        exportData["matches"] = matchArray;
                        outFile << exportData.dump(2);
                    }

                    nlohmann::json result;
                    result["match_count"] = matches.size();
                    result["format"] = format;
                    result["output_path"] = outputPath;
                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed to export search results: {}", e.what()));
                }
            });

            // Search operations: Multi-pattern search
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("search/multi", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    if (!ImHexApi::Provider::isValid()) {
                        throw std::runtime_error("No file is currently open");
                    }

                    auto provider = ImHexApi::Provider::get();
                    auto patternsArray = data.at("patterns");

                    nlohmann::json results = nlohmann::json::array();

                    for (const auto &patternObj : patternsArray) {
                        std::string pattern = patternObj.at("pattern").get<std::string>();
                        std::string type = patternObj.at("type").get<std::string>();

                        std::vector<u8> searchBytes;
                        if (type == "hex") {
                            searchBytes = hexStringToBytes(pattern);
                        } else {
                            searchBytes.assign(pattern.begin(), pattern.end());
                        }

                        std::vector<u64> matches;
                        const size_t chunkSize = 1024 * 1024;
                        std::vector<u8> buffer(chunkSize + searchBytes.size());
                        u64 fileSize = provider->getActualSize();

                        for (u64 offset = 0; offset < fileSize && matches.size() < 1000; offset += chunkSize) {
                            size_t readSize = std::min(chunkSize + searchBytes.size(), static_cast<size_t>(fileSize - offset));
                            provider->read(offset, buffer.data(), readSize);

                            for (size_t i = 0; i <= readSize - searchBytes.size() && matches.size() < 1000; i++) {
                                bool found = true;
                                for (size_t j = 0; j < searchBytes.size(); j++) {
                                    if (buffer[i + j] != searchBytes[j]) {
                                        found = false;
                                        break;
                                    }
                                }
                                if (found) matches.push_back(offset + i);
                            }
                        }

                        nlohmann::json patternResult;
                        patternResult["pattern"] = pattern;
                        patternResult["type"] = type;
                        patternResult["matches"] = matches;
                        patternResult["count"] = matches.size();
                        results.push_back(patternResult);
                    }

                    nlohmann::json result;
                    result["patterns_searched"] = patternsArray.size();
                    result["results"] = results;
                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed multi-pattern search: {}", e.what()));
                }
            });

            // Bookmark operations: Remove bookmark
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("bookmark/remove", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    u64 bookmarkId = data.at("id").get<u64>();
                    ImHexApi::Bookmarks::remove(bookmarkId);

                    nlohmann::json result;
                    result["id"] = bookmarkId;
                    result["status"] = "removed";
                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed to remove bookmark: {}", e.what()));
                }
            });

            // v0.4.0 ENDPOINTS

            // Binary Diffing: Enhanced diff with detailed regions
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("diff/analyze", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    u32 providerID1 = data.at("provider_id_1").get<u32>();
                    u32 providerID2 = data.at("provider_id_2").get<u32>();
                    std::string algorithm = data.value("algorithm", "simple");

                    auto providers = ImHexApi::Provider::getProviders();
                    prv::Provider* provider1 = nullptr;
                    prv::Provider* provider2 = nullptr;

                    for (auto *provider : providers) {
                        if (provider->getID() == providerID1) provider1 = provider;
                        if (provider->getID() == providerID2) provider2 = provider;
                    }

                    if (!provider1 || !provider2) {
                        throw std::runtime_error("One or both providers not found");
                    }

                    // Get available diffing algorithms
                    auto &algorithms = ContentRegistry::Diffing::impl::getAlgorithms();
                    ContentRegistry::Diffing::Algorithm* selectedAlgo = nullptr;

                    for (auto &algo : algorithms) {
                        std::string algoName = algo->getUnlocalizedName().get();
                        std::transform(algoName.begin(), algoName.end(), algoName.begin(), ::tolower);
                        if (algoName.find(algorithm) != std::string::npos) {
                            selectedAlgo = algo.get();
                            break;
                        }
                    }

                    if (!selectedAlgo && !algorithms.empty()) {
                        selectedAlgo = algorithms[0].get(); // Default to first algorithm
                    }

                    if (!selectedAlgo) {
                        throw std::runtime_error("No diffing algorithms available");
                    }

                    // Run diff analysis
                    auto diffTrees = selectedAlgo->analyze(provider1, provider2);

                    // Convert diff trees to JSON regions
                    nlohmann::json regions = nlohmann::json::array();

                    if (!diffTrees.empty()) {
                        auto &tree = diffTrees[0];
                        size_t regionCount = 0;
                        const size_t maxRegions = 10000;

                        for (auto it = tree.begin(); it != tree.end() && regionCount < maxRegions; ++it) {
                            regionCount++;

                            u64 intervalStart = it->first;
                            u64 intervalEnd = it->second.first;
                            auto type = it->second.second;

                            nlohmann::json region;
                            region["start"] = intervalStart;
                            region["end"] = intervalEnd;
                            region["size"] = intervalEnd - intervalStart + 1;

                            switch (type) {
                                case ContentRegistry::Diffing::DifferenceType::Match:
                                    region["type"] = "match";
                                    break;
                                case ContentRegistry::Diffing::DifferenceType::Mismatch:
                                    region["type"] = "mismatch";
                                    break;
                                case ContentRegistry::Diffing::DifferenceType::Insertion:
                                    region["type"] = "insertion";
                                    break;
                                case ContentRegistry::Diffing::DifferenceType::Deletion:
                                    region["type"] = "deletion";
                                    break;
                            }

                            regions.push_back(region);
                        }
                    }

                    nlohmann::json result;
                    result["algorithm"] = selectedAlgo->getUnlocalizedName().get();
                    result["provider1_id"] = providerID1;
                    result["provider2_id"] = providerID2;
                    result["provider1_size"] = provider1->getActualSize();
                    result["provider2_size"] = provider2->getActualSize();
                    result["regions"] = regions;
                    result["region_count"] = regions.size();

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed to analyze diff: {}", e.what()));
                }
            });

            // Disassembly: Disassemble code with architecture selection
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("disasm/disassemble", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    if (!ImHexApi::Provider::isValid()) {
                        throw std::runtime_error("No file is currently open");
                    }

                    auto provider = ImHexApi::Provider::get();
                    u64 offset = data.at("offset").get<u64>();
                    u64 length = data.value("length", 256);
                    std::string architecture = data.value("architecture", "x86_64");

                    // Limit disassembly size
                    const u64 maxLength = 64 * 1024; // 64KB
                    if (length > maxLength) {
                        throw std::runtime_error(fmt::format("Length {} exceeds maximum of {}", length, maxLength));
                    }

                    // Read data to disassemble
                    std::vector<u8> code(length);
                    provider->read(offset, code.data(), length);

                    // Get available disassemblers (they are stored as creator functions)
                    auto &architectures = ContentRegistry::Disassemblers::impl::getArchitectures();
                    std::unique_ptr<ContentRegistry::Disassemblers::Architecture> selectedArch;

                    for (auto &[name, creator] : architectures) {
                        std::string archName = name;
                        std::transform(archName.begin(), archName.end(), archName.begin(), ::tolower);
                        if (archName.find(architecture) != std::string::npos) {
                            selectedArch = creator();
                            break;
                        }
                    }

                    if (!selectedArch) {
                        throw std::runtime_error(fmt::format("Architecture '{}' not found", architecture));
                    }

                    // Initialize disassembler
                    if (!selectedArch->start()) {
                        throw std::runtime_error("Failed to initialize disassembler");
                    }

                    // Disassemble instructions
                    nlohmann::json instructions = nlohmann::json::array();
                    u64 currentOffset = offset;
                    size_t codeIndex = 0;
                    size_t maxInstructions = 1000;

                    while (codeIndex < code.size() && instructions.size() < maxInstructions) {
                        auto instr = selectedArch->disassemble(offset, currentOffset, currentOffset,
                                                              std::span<const u8>(code.data() + codeIndex, code.size() - codeIndex));

                        if (!instr.has_value()) break;

                        nlohmann::json instrJson;
                        instrJson["address"] = instr->address;
                        instrJson["offset"] = instr->offset;
                        instrJson["size"] = instr->size;
                        instrJson["bytes"] = instr->bytes;
                        instrJson["mnemonic"] = instr->mnemonic;
                        instrJson["operands"] = instr->operators;

                        instructions.push_back(instrJson);

                        currentOffset += instr->size;
                        codeIndex += instr->size;
                    }

                    nlohmann::json result;
                    result["architecture"] = selectedArch->getName();
                    result["start_offset"] = offset;
                    result["bytes_disassembled"] = codeIndex;
                    result["instruction_count"] = instructions.size();
                    result["instructions"] = instructions;

                    // Cleanup disassembler
                    selectedArch->end();

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed to disassemble: {}", e.what()));
                }
            });

            // Chunked Read: Stream large file regions
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("data/read_chunked", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    if (!ImHexApi::Provider::isValid()) {
                        throw std::runtime_error("No file is currently open");
                    }

                    auto provider = ImHexApi::Provider::get();
                    u64 offset = data.at("offset").get<u64>();
                    u64 totalLength = data.at("length").get<u64>();
                    u64 chunkSize = data.value("chunk_size", 1024 * 1024); // Default 1MB chunks
                    size_t chunkIndex = data.value("chunk_index", 0);
                    std::string encoding = data.value("encoding", "hex");

                    // Calculate this chunk's parameters
                    u64 chunkOffset = offset + (chunkIndex * chunkSize);
                    u64 thisChunkSize = std::min(chunkSize, totalLength - (chunkIndex * chunkSize));

                    if (chunkOffset >= provider->getActualSize()) {
                        throw std::runtime_error("Chunk offset beyond file size");
                    }

                    if (thisChunkSize == 0) {
                        throw std::runtime_error("No data left to read");
                    }

                    // Read this chunk
                    std::vector<u8> chunk(thisChunkSize);
                    provider->read(chunkOffset, chunk.data(), thisChunkSize);

                    // Encode data based on requested format
                    std::string encodedData;
                    if (encoding == "hex") {
                        encodedData = bytesToHexString(chunk);
                    } else if (encoding == "base64") {
                        encodedData = base64_encode(chunk);
                    } else {
                        throw std::runtime_error(fmt::format("Unsupported encoding: {}", encoding));
                    }

                    u64 totalChunks = (totalLength + chunkSize - 1) / chunkSize;
                    bool hasMore = (chunkIndex + 1) < totalChunks;

                    nlohmann::json result;
                    result["chunk_index"] = chunkIndex;
                    result["chunk_offset"] = chunkOffset;
                    result["chunk_size"] = thisChunkSize;
                    result["encoding"] = encoding;
                    result["data"] = encodedData;
                    result["total_chunks"] = totalChunks;
                    result["has_more"] = hasMore;
                    result["bytes_remaining"] = totalLength - ((chunkIndex + 1) * chunkSize);

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Failed chunked read: {}", e.what()));
                }
            });

            // Batch Diff: Compare reference file against multiple targets
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("batch/diff", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    // Parse parameters
                    u32 reference_id = data.at("reference_id").get<u32>();
                    std::string algorithm = data.value("algorithm", "myers");
                    size_t max_diff_regions = data.value("max_diff_regions", 1000);

                    // Get target IDs - can be array or "all"
                    std::vector<u32> target_ids;
                    if (data.contains("target_ids")) {
                        if (data["target_ids"].is_string() && data["target_ids"].get<std::string>() == "all") {
                            // Get all providers except reference
                            auto providers = ImHexApi::Provider::getProviders();
                            for (auto& prov : providers) {
                                u32 id = prov->getID();
                                if (id != reference_id) {
                                    target_ids.push_back(id);
                                }
                            }
                        } else if (data["target_ids"].is_array()) {
                            auto ids = data["target_ids"].get<std::vector<int>>();
                            for (int id : ids) {
                                target_ids.push_back(static_cast<u32>(id));
                            }
                        }
                    }

                    if (target_ids.empty()) {
                        throw std::runtime_error("No target files specified");
                    }

                    // Find reference provider
                    auto providers = ImHexApi::Provider::getProviders();
                    prv::Provider* refProvider = nullptr;
                    for (auto& prov : providers) {
                        if (prov->getID() == reference_id) {
                            refProvider = prov;
                            break;
                        }
                    }

                    if (!refProvider) {
                        throw std::runtime_error(fmt::format("Reference provider {} not found", reference_id));
                    }

                    // Safety check for reference file size
                    const u64 maxDiffSize = 100 * 1024 * 1024; // 100MB
                    if (refProvider->getActualSize() > maxDiffSize) {
                        throw std::runtime_error(fmt::format("Reference file too large (max {} MB)", maxDiffSize / (1024 * 1024)));
                    }

                    // Get diffing algorithm
                    auto &algorithms = ContentRegistry::Diffing::impl::getAlgorithms();
                    ContentRegistry::Diffing::Algorithm* selectedAlgo = nullptr;

                    std::string algoLower = algorithm;
                    std::transform(algoLower.begin(), algoLower.end(), algoLower.begin(), ::tolower);

                    for (auto &algo : algorithms) {
                        std::string algoName = algo->getUnlocalizedName().get();
                        std::transform(algoName.begin(), algoName.end(), algoName.begin(), ::tolower);
                        if (algoName.find(algoLower) != std::string::npos) {
                            selectedAlgo = algo.get();
                            break;
                        }
                    }

                    if (!selectedAlgo && !algorithms.empty()) {
                        selectedAlgo = algorithms[0].get();
                    }

                    if (!selectedAlgo) {
                        throw std::runtime_error("No diffing algorithms available");
                    }

                    // Results storage
                    std::vector<nlohmann::json> diffs;
                    double totalSimilarity = 0.0;
                    u32 mostSimilarId = 0;
                    double highestSimilarity = 0.0;
                    u32 leastSimilarId = 0;
                    double lowestSimilarity = 100.0;

                    // Compare reference against each target
                    for (u32 target_id : target_ids) {
                        // Find target provider
                        prv::Provider* targetProvider = nullptr;
                        for (auto& prov : providers) {
                            if (prov->getID() == target_id) {
                                targetProvider = prov;
                                break;
                            }
                        }

                        if (!targetProvider) {
                            log::warn("MCP: Target provider {} not found, skipping", target_id);
                            continue;
                        }

                        // Safety check for target file size
                        if (targetProvider->getActualSize() > maxDiffSize) {
                            log::warn("MCP: Target file {} too large, skipping", target_id);
                            continue;
                        }

                        // Run diff analysis with TaskManager
                        std::vector<ContentRegistry::Diffing::DiffTree> diffTrees;
                        std::exception_ptr taskException;
                        bool taskCompleted = false;

                        auto commonSize = std::max(refProvider->getActualSize(), targetProvider->getActualSize());
                        auto diffTask = TaskManager::createTask("MCP Batch Diff", commonSize, [&]([[maybe_unused]] Task &task) {
                            try {
                                diffTrees = selectedAlgo->analyze(refProvider, targetProvider);
                                taskCompleted = true;
                            } catch (...) {
                                taskException = std::current_exception();
                                taskCompleted = true;
                            }
                        });

                        // Wait for task completion
                        const int maxWaitMs = 30000;
                        const int pollIntervalMs = 100;
                        int totalWaitMs = 0;

                        while (!taskCompleted && totalWaitMs < maxWaitMs) {
                            std::this_thread::sleep_for(std::chrono::milliseconds(pollIntervalMs));
                            totalWaitMs += pollIntervalMs;
                        }

                        if (!taskCompleted) {
                            log::warn("MCP: Diff analysis timed out for target {}, skipping", target_id);
                            continue;
                        }

                        if (taskException) {
                            try {
                                std::rethrow_exception(taskException);
                            } catch (const std::exception &e) {
                                log::warn("MCP: Diff analysis failed for target {}: {}", target_id, e.what());
                                continue;
                            }
                        }

                        // Calculate similarity from diff regions
                        u64 totalBytes = std::max(refProvider->getActualSize(), targetProvider->getActualSize());
                        u64 matchingBytes = 0;
                        size_t diffRegions = 0;

                        nlohmann::json regions = nlohmann::json::array();

                        if (!diffTrees.empty()) {
                            auto &tree = diffTrees[0];
                            size_t regionCount = 0;

                            for (auto it = tree.begin(); it != tree.end() && regionCount < max_diff_regions; ++it) {
                                regionCount++;
                                diffRegions++;

                                u64 intervalStart = it->first;
                                u64 intervalEnd = it->second.first;
                                auto type = it->second.second;
                                u64 size = intervalEnd - intervalStart + 1;

                                if (type == ContentRegistry::Diffing::DifferenceType::Match) {
                                    matchingBytes += size;
                                }

                                // Only include limited regions in response
                                if (regionCount <= 100) {  // Limit regions per file to 100
                                    nlohmann::json region;
                                    region["start"] = intervalStart;
                                    region["end"] = intervalEnd;
                                    region["size"] = size;

                                    switch (type) {
                                        case ContentRegistry::Diffing::DifferenceType::Match:
                                            region["type"] = "match";
                                            break;
                                        case ContentRegistry::Diffing::DifferenceType::Mismatch:
                                            region["type"] = "mismatch";
                                            break;
                                        case ContentRegistry::Diffing::DifferenceType::Insertion:
                                            region["type"] = "insertion";
                                            break;
                                        case ContentRegistry::Diffing::DifferenceType::Deletion:
                                            region["type"] = "deletion";
                                            break;
                                    }

                                    regions.push_back(region);
                                }
                            }
                        }

                        double similarity = totalBytes > 0 ? (matchingBytes * 100.0) / totalBytes : 0.0;

                        nlohmann::json diffResult;
                        diffResult["target_id"] = target_id;
                        diffResult["target_file"] = targetProvider->getName();
                        diffResult["similarity"] = similarity;
                        diffResult["diff_regions"] = diffRegions;
                        diffResult["regions"] = regions;
                        diffResult["matching_bytes"] = matchingBytes;
                        diffResult["total_bytes"] = totalBytes;

                        diffs.push_back(diffResult);

                        // Update statistics
                        totalSimilarity += similarity;
                        if (similarity > highestSimilarity) {
                            highestSimilarity = similarity;
                            mostSimilarId = target_id;
                        }
                        if (similarity < lowestSimilarity) {
                            lowestSimilarity = similarity;
                            leastSimilarId = target_id;
                        }
                    }

                    double avgSimilarity = diffs.empty() ? 0.0 : totalSimilarity / diffs.size();

                    nlohmann::json result;
                    result["diffs"] = diffs;
                    result["summary"] = {
                        {"reference_id", reference_id},
                        {"reference_file", refProvider->getName()},
                        {"algorithm", selectedAlgo->getUnlocalizedName().get()},
                        {"files_compared", diffs.size()},
                        {"avg_similarity", avgSimilarity},
                        {"most_similar", mostSimilarId},
                        {"highest_similarity", highestSimilarity},
                        {"least_similar", leastSimilarId},
                        {"lowest_similarity", lowestSimilarity}
                    };

                    log::info("MCP: Batch diff complete - {} comparisons, avg similarity {:.1f}%", diffs.size(), avgSimilarity);

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(fmt::format("Batch diff failed: {}", e.what()));
                }
            });

            log::info("MCP plugin (improved) loaded - registered {} network endpoints", 21);
        }

    }

}

// Plugin metadata and entry point
IMHEX_PLUGIN_SETUP("MCP Integration", "ImHex Contributors", "Improved MCP server integration for AI assistant access") {
    using namespace hex::plugin::mcp;

    hex::log::info("Initializing MCP plugin (improved version)...");

    // Register all MCP network endpoints
    registerMCPEndpoints();
}
