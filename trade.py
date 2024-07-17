import asyncio

import os
import sys
import site

current_dir = os.path.dirname(os.path.abspath(__file__))
libs_dir = os.path.join(current_dir, 'libs')

activate_this = os.path.join(libs_dir, 'venv', 'Scripts', 'activate_this.py')
exec(open(activate_this).read(), {'__file__': activate_this})

# Update sys.path
site.main()

from libs.jupiter import trade

if __name__ == "__main__":
    asyncio.run(
        trade("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "So11111111111111111111111111111111111111112", 780000,
              60))
