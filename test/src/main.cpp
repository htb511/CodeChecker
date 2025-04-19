#include <iostream>

#include "test.hpp"

int functionx()
{
#ifdef DEBUG
    function();
#endif
    return 0;
}

int main()
{
    LOG("Hello");
    functionx();
    return 0;
}
