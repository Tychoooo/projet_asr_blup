#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <string>
#include "mylib.h"

namespace py = pybind11;

static constexpr std::size_t MAX_PARAMS       = 16;
static constexpr std::size_t FIELDS_PER_EVENT = 7 + MAX_PARAMS;

void load_trace_py(const std::string &path)
{
    if (load_trace(path.c_str()) != 0) {
        throw std::runtime_error("Failed to load trace file: " + path);
    }
}


py::array_t<long long> get_data_py()
{
    size_t n = 0;
    const df_value_t* data = get_data(&n);

    if (!data) {
        throw std::runtime_error("Internal data buffer is null. Did you call load_trace()?");
    }
    if (n % FIELDS_PER_EVENT != 0) {
        throw std::runtime_error("DATA_SIZE is not a multiple of FIELDS_PER_EVENT");
    }

    std::size_t nb_events = n / FIELDS_PER_EVENT;

    return py::array_t<long long>(
        {nb_events, FIELDS_PER_EVENT},                // dimensions
        {FIELDS_PER_EVENT * sizeof(long long),        // stride ligne
         sizeof(long long)},                          // stride colonne
        reinterpret_cast<const long long*>(data)      // pointeur vers les données
    );
}


PYBIND11_MODULE(mini, m)
{
    m.doc() = "Module for loading FXT trace files and accessing data as Numpy arrays";

    m.def("load_trace", &load_trace_py,
          "Load an FXT trace file");

    m.def("get_data", &get_data_py,
          "Return a Numpy array corresponding to the trace loaded");
}
