#include <hex/plugin.hpp>

#include <hex/api/imhex_api/provider.hpp>
#include <hex/api/imhex_api/bookmarks.hpp>
#include <hex/api/content_registry/communication_interface.hpp>
#include <hex/api/events/requests_interaction.hpp>
#include <hex/providers/provider.hpp>

#include <hex/helpers/logger.hpp>
#include <hex/helpers/crypto.hpp>
#include <hex/helpers/utils.hpp>

#include <nlohmann/json.hpp>

#include <vector>
#include <string>
#include <algorithm>

namespace hex::plugin::mcp {

    namespace {

        /**
         * Convert hex string to bytes
         */
        std::vector<u8> hexStringToBytes(const std::string &hexStr) {
            std::vector<u8> bytes;
            bytes.reserve(hexStr.length() / 2);

            for (size_t i = 0; i < hexStr.length(); i += 2) {
                std::string byteString = hexStr.substr(i, 2);
                u8 byte = static_cast<u8>(std::strtol(byteString.c_str(), nullptr, 16));
                bytes.push_back(byte);
            }

            return bytes;
        }

        /**
         * Convert bytes to hex string
         */
        std::string bytesToHexString(const std::vector<u8> &bytes) {
            std::string hexStr;
            hexStr.reserve(bytes.size() * 2);

            for (u8 byte : bytes) {
                char hex[3];
                std::sprintf(hex, "%02X", byte);
                hexStr += hex;
            }

            return hexStr;
        }

        /**
         * Register MCP network endpoints
         */
        void registerMCPEndpoints() {
            // File operations: Open file
            ContentRegistry::CommunicationInterface::registerNetworkEndpoint("file/open", [](const nlohmann::json &data) -> nlohmann::json {
                try {
                    auto path = data.at("path").get<std::string>();

                    log::info("MCP: Opening file '{}'", path);

                    // Request to open file via event system
                    RequestOpenFile::post(path);

                    nlohmann::json result;
                    result["file"] = path;

                    // Get file size if provider is available
                    if (ImHexApi::Provider::isValid()) {
                        auto provider = ImHexApi::Provider::get();
                        if (provider != nullptr) {
                            result["size"] = provider->getActualSize();
                            result["name"] = provider->getName();
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
                        throw std::runtime_error("Offset is beyond file size");
                    }

                    if (offset + length > provider->getActualSize()) {
                        length = provider->getActualSize() - offset;
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
                        throw std::runtime_error("Offset is beyond file size");
                    }

                    // Write data
                    provider->write(offset, bytes.data(), bytes.size());
                    ImHexApi::Provider::markDirty();

                    nlohmann::json result;
                    result["offset"] = offset;
                    result["length"] = bytes.size();
                    result["written"] = true;

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
                        throw std::runtime_error("Offset is beyond file size");
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
                        types["int8"] = static_cast<i8>(buffer[0]);
                        types["uint8"] = buffer[0];
                    }

                    if (maxBytes >= 2) {
                        i16 i16val;
                        u16 u16val;
                        std::memcpy(&i16val, buffer.data(), sizeof(i16));
                        std::memcpy(&u16val, buffer.data(), sizeof(u16));
                        types["int16"] = i16val;
                        types["uint16"] = u16val;
                    }

                    if (maxBytes >= 4) {
                        i32 i32val;
                        u32 u32val;
                        float floatval;
                        std::memcpy(&i32val, buffer.data(), sizeof(i32));
                        std::memcpy(&u32val, buffer.data(), sizeof(u32));
                        std::memcpy(&floatval, buffer.data(), sizeof(float));
                        types["int32"] = i32val;
                        types["uint32"] = u32val;
                        types["float"] = floatval;
                    }

                    if (maxBytes >= 8) {
                        i64 i64val;
                        u64 u64val;
                        double doubleval;
                        std::memcpy(&i64val, buffer.data(), sizeof(i64));
                        std::memcpy(&u64val, buffer.data(), sizeof(u64));
                        std::memcpy(&doubleval, buffer.data(), sizeof(double));
                        types["int64"] = i64val;
                        types["uint64"] = u64val;
                        types["double"] = doubleval;
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

                    // Hex dump
                    types["hex"] = bytesToHexString(buffer);

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
                    std::string hashHex;

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

                    hashHex = bytesToHexString(hashResult);

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

            // Search: Find pattern in data
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

                    // Simple search implementation - read file in chunks and search
                    std::vector<u64> matches;
                    const size_t chunkSize = 1024 * 1024; // 1 MB chunks
                    std::vector<u8> buffer(chunkSize + searchBytes.size());

                    u64 fileSize = provider->getActualSize();
                    for (u64 offset = 0; offset < fileSize; offset += chunkSize) {
                        size_t readSize = std::min(chunkSize + searchBytes.size(), static_cast<size_t>(fileSize - offset));
                        provider->read(offset, buffer.data(), readSize);

                        // Search for pattern in this chunk
                        for (size_t i = 0; i <= readSize - searchBytes.size(); i++) {
                            bool found = true;
                            for (size_t j = 0; j < searchBytes.size(); j++) {
                                if (buffer[i + j] != searchBytes[j]) {
                                    found = false;
                                    break;
                                }
                            }
                            if (found) {
                                matches.push_back(offset + i);
                                if (matches.size() >= 1000) {
                                    break; // Limit to 1000 matches
                                }
                            }
                        }

                        if (matches.size() >= 1000) {
                            break;
                        }
                    }

                    nlohmann::json result;
                    result["pattern"] = pattern;
                    result["type"] = searchType;
                    result["matches"] = matches;
                    result["count"] = matches.size();

                    return result;
                } catch (const std::exception &e) {
                    throw std::runtime_error(hex::format("Failed to search: {}", e.what()));
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
                    } else {
                        result["valid"] = false;
                    }
                } else {
                    result["valid"] = false;
                }

                return result;
            });

            log::info("MCP plugin loaded - registered {} network endpoints", 8);
        }

    }

}

// Plugin metadata and entry point
IMHEX_PLUGIN_SETUP("MCP Integration", "ImHex Contributors", "MCP server integration for AI assistant access") {
    using namespace hex::plugin::mcp;

    log::info("Initializing MCP plugin...");

    // Register all MCP network endpoints
    registerMCPEndpoints();
}
