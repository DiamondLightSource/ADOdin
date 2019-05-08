//
// Created by gnx91527 on 31/10/18.
//
#include "OdinLiveViewListener.h"
#include <iostream>

OdinLiveViewListener::OdinLiveViewListener() :
    ctx_(1),
    socket_(ctx_, ZMQ_SUB),
    connected_(false)
{

}

OdinLiveViewListener::~OdinLiveViewListener()
{

}

void OdinLiveViewListener::connect(const std::string& endpoint)
{
    if (connected_){
        this->disconnect();
    }
    endpoint_ = endpoint;
    socket_.connect(endpoint.c_str());
    socket_.setsockopt(ZMQ_SUBSCRIBE, "", 0);
    connected_ = true;
}

void OdinLiveViewListener::disconnect()
{
    socket_.disconnect(endpoint_.c_str());
    connected_ = false;
}

bool OdinLiveViewListener::listen_for_frame(long timeout)
{
    bool frame_received = false;
    //  Poll socket for a reply, with timeout
    zmq::pollitem_t items[] = { { socket_, 0, ZMQ_POLLIN, 0 } };
    zmq::poll (&items[0], 1, timeout);

    //  If we got a reply, notify
    if (items[0].revents & ZMQ_POLLIN) {
        frame_received = true;
    }
    return frame_received;
}

ImageDescription OdinLiveViewListener::read_full_image()
{
    this->read_header();
    this->read_frame();
    return image_;
}

void OdinLiveViewListener::read_header()
{
    // Read the first message.  This should be a JSON format string
    // defining the rest of the frame
    socket_.recv(&header_, 0);
    //printf("Received Frame Header %zd bytes: \"%s\"\n", header_.size(), (char *)header_.data());
    // Attempt to decode the header into a JSON object
    char header_str[header_.size()+1];
    memcpy(header_str, header_.data(), header_.size());
    header_str[header_.size()] = '\0';
    parse_json_header(header_str);
}

void OdinLiveViewListener::read_frame()
{
    socket_.recv(&frame_, 0);
    //printf("Received Frame body %zd bytes\n", frame_.size());
    image_.bytes = frame_.size();
    image_.dPtr = frame_.data();
}

void OdinLiveViewListener::parse_json_header(const std::string& header_str)
{
    // Reset the image validity
    image_.valid = true;
    // Parse the message, catching any unexpected exceptions from rapidjson
    try {
        doc_.Parse(header_str.c_str());
        // Test if the message parsed correctly, otherwise set the validity to false
        if (doc_.HasParseError())
        {
            image_.valid = false;
        }

        rapidjson::Value::ConstMemberIterator itr = doc_.FindMember("frame_num");
        if (itr == doc_.MemberEnd())
        {
            image_.valid = false;
        } else {
            image_.number = itr->value.GetInt();
        }

        itr = doc_.FindMember("dtype");
        if (itr == doc_.MemberEnd())
        {
            image_.valid = false;
        } else {
            image_.dtype = itr->value.GetString();
        }

        itr = doc_.FindMember("shape");
        if (itr == doc_.MemberEnd())
        {
            image_.valid = false;
        } else {
            std::string val = itr->value[1].GetString();
            sscanf(val.c_str(), "%zu", &(image_.width));
            val = itr->value[0].GetString();
            sscanf(val.c_str(), "%zu", &(image_.height));
        }
    }
    catch (...) {
        image_.valid = false;
    }
}

