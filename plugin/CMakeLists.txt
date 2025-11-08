cmake_minimum_required(VERSION 3.16)

include(ImHexPlugin)

# Create the MCP plugin
add_imhex_plugin(
    NAME
        mcp

    SOURCES
        source/plugin_mcp.cpp

    LIBRARIES
        libimhex
)
