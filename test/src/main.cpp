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
    if (1==1)
        functionx();
    else
        function();
    return 0;
}
