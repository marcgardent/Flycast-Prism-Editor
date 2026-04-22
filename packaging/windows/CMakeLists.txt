cmake_minimum_required(VERSION 3.10)
project(FlycastViewerWindowsPackaging NONE)

# Get Git revision (first 5 characters)
execute_process(
    COMMAND git rev-parse --short=5 HEAD
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    OUTPUT_VARIABLE GIT_REV
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)

# Get current date
string(TIMESTAMP BUILD_DATE "%Y%m%d")

set(DOCKER_IMAGE "flycast-viewer-win-builder")
set(ROOT_DIR "${CMAKE_SOURCE_DIR}")

# Target to build the Windows Docker image
add_custom_target(docker-build-win
    COMMAND docker build -t ${DOCKER_IMAGE} -f ${CMAKE_CURRENT_SOURCE_DIR}/Dockerfile ${ROOT_DIR}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Building Windows Docker build image (Wine + PyInstaller)"
)

# Target to generate the Windows EXE
add_custom_target(publish-win
    DEPENDS check-git-clean docker-build-win
    COMMAND ${CMAKE_COMMAND} -E make_directory ${ROOT_DIR}/output
    COMMAND docker run --rm 
        -v ${ROOT_DIR}:/src 
        -v ${ROOT_DIR}/output:/src/output 
        -e GIT_REV=${GIT_REV} 
        -e BUILD_DATE=${BUILD_DATE} 
        ${DOCKER_IMAGE}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Generating Windows EXE in output/ directory"
)
