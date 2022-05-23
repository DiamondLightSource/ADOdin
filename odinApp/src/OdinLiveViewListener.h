//
// Created by gnx91527 on 31/10/18.
//

#ifndef ADODIN_ODINLIVEVIEWLISTENER_H
#define ADODIN_ODINLIVEVIEWLISTENER_H

#include <string>
#include <exception>
#include <vector>
#include "zmq.hpp"

// Override rapidsjon assertion mechanism before including appropriate headers
#ifdef RAPIDJSON_ASSERT
#undef RAPIDJSON_ASSERT
#endif
#define RAPIDJSON_ASSERT(x) if (!(x)) throw std::exception();
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/error/en.h"

struct ImageDescription
{
    bool valid;
    int number;
    std::string dtype;
    size_t width;
    size_t height;
    size_t bytes;
    void *dPtr;
};


class OdinLiveViewListener
{
public:
    OdinLiveViewListener();

    virtual ~OdinLiveViewListener();

    void connect(const std::string& endpoint);
    void disconnect();

    bool listen_for_frame(long timeout=-1);
    ImageDescription read_full_image();
    void read_header();
    void read_frame();

    void parse_json_header(const std::string& header_str);

    std::string get_last_image_header();
    std::string get_last_image_invalid_reason();
    bool get_last_image_valid();
    uint32_t get_image_counter();

private:
    std::string endpoint_;
    zmq::context_t ctx_;
    zmq::socket_t socket_;
    bool connected_;
    zmq::message_t header_;
    zmq::message_t frame_;
    ImageDescription image_;
    rapidjson::Document doc_;
    std::string last_image_header_;
    std::string last_image_invalid_reason_;
    bool last_image_valid_;
    uint32_t image_counter_;
};

#endif //ADODIN_ODINLIVEVIEWLISTENER_H
