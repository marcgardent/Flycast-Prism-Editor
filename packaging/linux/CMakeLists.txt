cmake_minimum_required(VERSION 3.10)
project(FlycastViewerPackaging NONE)

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

set(DOCKER_IMAGE "flycast-viewer-builder")
set(ROOT_DIR "${CMAKE_SOURCE_DIR}")

# Target to check if Git is clean
add_custom_target(check-git-clean
    COMMAND bash -c "git status --porcelain | grep -q . && (echo 'ERROR: Uncommitted changes found! Please commit or stash your changes before publishing.' && exit 1) || exit 0"
    WORKING_DIRECTORY ${ROOT_DIR}
    COMMENT "Checking for a clean Git state..."
)

# Target to build the Docker image
add_custom_target(docker-build
    COMMAND docker build -t ${DOCKER_IMAGE} -f ${CMAKE_CURRENT_SOURCE_DIR}/Dockerfile ${ROOT_DIR}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Building Docker build image"
)

# Target to generate the AppImage
add_custom_target(publish
    DEPENDS check-git-clean docker-build
    COMMAND ${CMAKE_COMMAND} -E make_directory ${ROOT_DIR}/output
    COMMAND docker run --rm 
        -v ${ROOT_DIR}:/build/source 
        -v ${ROOT_DIR}/output:/build/output 
        -e GIT_REV=${GIT_REV} 
        -e BUILD_DATE=${BUILD_DATE} 
        ${DOCKER_IMAGE}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Generating AppImage in output/ directory"
)
