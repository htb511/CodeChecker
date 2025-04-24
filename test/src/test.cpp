#include "test.hpp"

class Client
{
public: 
    void run();
    void init();

private:
    int x;
};

void Client::run()
{
    function();
}

void Client::init()
{

}

Client c;

int function_6()
{
    return 0;
}

int function_5()
{
    function_6();
    return 0;
}

int function_4()
{
    function_5();
    return 0;
}

int function_3()
{
    LOG("Hello");
    function_5();
    function_6();
    return 0;
}

int function_2()
{
    function_3();
    function_4();
    function_6();
    return 0;
}

int function()
{
    function_2();
    return 0;
}

