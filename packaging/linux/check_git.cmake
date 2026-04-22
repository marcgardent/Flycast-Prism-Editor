execute_process(
    COMMAND git status --porcelain
    OUTPUT_VARIABLE GIT_STATUS
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

if(NOT "${GIT_STATUS}" STREQUAL "")
    message(FATAL_ERROR "\nERROR: Uncommitted changes found!\n${GIT_STATUS}\n\nPlease commit or stash your changes before publishing.")
endif()
