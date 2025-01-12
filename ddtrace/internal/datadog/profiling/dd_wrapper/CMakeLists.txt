cmake_minimum_required(VERSION 3.19)
project(dd_wrapper
    VERSION 0.1.1
    LANGUAGES CXX
)

# Infer some basic properties about the build.  This is necessary because multiple
# extensions reuse this cmake file, so we need its artifacts to go in a consistent
# place
get_filename_component(dd_wrapper_BUILD_PARENT "${CMAKE_BINARY_DIR}/../.." ABSOLUTE)
set(dd_wrapper_BUILD_DIR "${dd_wrapper_BUILD_PARENT}/ddtrace.internal.datadog.profiling")

# Custom modules are in the parent directory
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../cmake")

# Setup state for FindLibdatadog
set(Datadog_BUILD_DIR "${dd_wrapper_BUILD_PARENT}/libdatadog")

# Includes
include(CMakePackageConfigHelpers) # For generating the config file
include(FetchContent)
include(ExternalProject)
include(FindLibdatadog)
include(FindCppcheck)

# Send some of these vars back up to the parent
if (DD_WRAPPER_IS_SUBPROJECT)
  set(Datadog_INCLUDE_DIRS "${Datadog_INCLUDE_DIRS}" PARENT_SCOPE)
  set(dd_wrapper_BUILD_DIR "${dd_wrapper_BUILD_PARENT}/ddtrace.internal.datadog.profiling" PARENT_SCOPE)
endif()

add_compile_options(
  "$<$<CONFIG:Debug>:-Og;-ggdb3>"
  "$<$<CONFIG:Release>:-Os -s>"
  -fno-semantic-interposition -Wall -Werror -Wextra -Wshadow -Wnon-virtual-dtor -Wold-style-cast
)

# Library sources
add_library(dd_wrapper SHARED
    src/uploader_builder.cpp
    src/sample_manager.cpp
    src/profile.cpp
    src/uploader.cpp
    src/sample.cpp
    src/interface.cpp
)

# At present, C++17 is chosen as the minimum standard. This conflicts with the
# manylinux2014 standard upon which we must rely. We'll have to statically link
# libstdc++ to avoid this conflict, but need to remain mindful of symbol visibility
# and overall binary size.
target_compile_features(dd_wrapper PUBLIC cxx_std_17)

# Set some linker options
target_compile_options(dd_wrapper PRIVATE -fno-semantic-interposition)
target_compile_options(dd_wrapper PRIVATE -ffunction-sections -fdata-sections)
target_link_options(dd_wrapper PRIVATE -static-libstdc++)
target_link_options(dd_wrapper PRIVATE -Wl,-Bsymbolic-functions)
target_link_options(dd_wrapper PRIVATE -Wl,--gc-sections)
set_property(TARGET dd_wrapper PROPERTY INTERPROCEDURAL_OPTIMIZATION TRUE)

target_include_directories(dd_wrapper PRIVATE
    include
    ${Datadog_INCLUDE_DIRS}
)
target_link_libraries(dd_wrapper PRIVATE
    ${Datadog_LIBRARIES}
)
set_target_properties(dd_wrapper PROPERTIES POSITION_INDEPENDENT_CODE ON)

set_target_properties(dd_wrapper
    PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${dd_wrapper_BUILD_DIR}"
)

# If DO_FANALYZER is specified and we're using gcc, then we can use -fanalyzer
if (DO_FANALYZER AND CMAKE_CXX_COMPILER_ID MATCHES "GNU")
  target_compile_options(dd_wrapper PRIVATE -fanalyzer)
endif()

# If DO_CPPCHECK is specified, then we can use cppcheck
add_cppcheck_target(cppcheck_dd_wrapper ${CMAKE_CURRENT_SOURCE_DIR})

# Propagate sanitizers
if (SANITIZE_OPTIONS)
    # Some sanitizers (or the analysis--such as symbolization--tooling thereof) work better with frame
    # pointers, so we include it here.
    target_compile_options(dd_wrapper PRIVATE -fsanitize=${SANITIZE_OPTIONS} -fno-omit-frame-pointer)
    target_link_options(dd_wrapper PRIVATE -fsanitize=${SANITIZE_OPTIONS})
endif()

# If dd_wrapper_INSTALL_DIR is specified by the parent, use it
if (NOT dd_wrapper_INSTALL_DIR)
  # If not, then just keep it in the build directory
  set(dd_wrapper_INSTALL_DIR "${CMAKE_BINARY_DIR}/lib")
endif()
message(STATUS "dd_wrapper_INSTALL_DIR: ${dd_wrapper_INSTALL_DIR}")
install(TARGETS dd_wrapper
    DESTINATION ${dd_wrapper_INSTALL_DIR}
)

# Add the tests
if (BUILD_TESTING)
    enable_testing()
    add_subdirectory(test)
endif()
