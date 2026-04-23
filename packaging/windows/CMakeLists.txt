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

set(DOCKER_IMAGE "flycast-prism-editor-win-builder")
set(ROOT_DIR "${CMAKE_SOURCE_DIR}")
set(VERSION_STR "")
if(GIT_REV)
    set(VERSION_STR "-${GIT_REV}")
endif()
if(BUILD_DATE)
    set(VERSION_STR "${VERSION_STR}-${BUILD_DATE}")
endif()

# Target to build the Windows Docker image
add_custom_target(docker-build-win
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/sync_requirements.py
    COMMAND docker build -t ${DOCKER_IMAGE} -f ${CMAKE_CURRENT_SOURCE_DIR}/Dockerfile ${ROOT_DIR}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Syncing requirements and building Windows Docker build image"
)

# Target to generate the Windows EXE
add_custom_target(publish-win
    DEPENDS check-git-clean docker-build-win
    COMMAND ${CMAKE_COMMAND} -E make_directory ${ROOT_DIR}/output
    # The batonogov image builds into /src/dist/ which is mapped to ${ROOT_DIR}/dist/
    COMMAND docker run --rm 
        -v ${ROOT_DIR}:/src 
        -e SPECFILE=flycast-prism-editor.spec
        ${DOCKER_IMAGE}
    # Rename and move the output to the output/ directory
    COMMAND ${CMAKE_COMMAND} -E rename ${ROOT_DIR}/dist/flycast-prism-editor.exe ${ROOT_DIR}/output/Flycast_Prism_Editor${VERSION_STR}.exe
    COMMAND ${CMAKE_COMMAND} -E remove_directory ${ROOT_DIR}/build
    COMMAND ${CMAKE_COMMAND} -E remove_directory ${ROOT_DIR}/dist
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Generating Windows EXE in output/ directory"
)
