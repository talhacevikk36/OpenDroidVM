cmake_minimum_required(VERSION 3.16)
project(OpenDroidVM VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)
FetchContent_Declare(
  json
  URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
)
FetchContent_MakeAvailable(json)

add_executable(opendroidwm
  src/main.cpp
  src/profile.cpp
  src/launcher.cpp
)
target_include_directories(opendroidwm PRIVATE src)
target_link_libraries(opendroidwm PRIVATE nlohmann_json::nlohmann_json)

if(MSVC)
  target_compile_options(opendroidwm PRIVATE /W4 /utf-8)
else()
  target_compile_options(opendroidwm PRIVATE -Wall -Wextra)
endif()

# profiles klasorunu exe'nin yanina kopyala
add_custom_command(TARGET opendroidwm POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E copy_directory
          ${CMAKE_SOURCE_DIR}/opendroidvm/profiles $<TARGET_FILE_DIR:opendroidwm>/profiles)

install(TARGETS opendroidwm RUNTIME DESTINATION .)
install(DIRECTORY opendroidvm/profiles DESTINATION .)
