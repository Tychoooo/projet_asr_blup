cmake_minimum_required(VERSION 3.14.0)
project(mini_api C CXX)
set(CMAKE_CXX_STANDARD 20)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(pybind11 CONFIG REQUIRED)

find_library(FXT_LIB fxt REQUIRED)

add_library(mylib STATIC mylib.c)
target_link_libraries(mylib PRIVATE ${FXT_LIB})

pybind11_add_module(mini MODULE bindings.cpp)
target_link_libraries(mini PRIVATE mylib ${FXT_LIB})
