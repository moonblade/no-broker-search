# read whats in the clipboard

import os
import pyperclip

text = pyperclip.paste()

# append the text to ignore_list.txt in folder that the script is located in with os.path.dirname(__file__)
with open(os.path.join(os.path.dirname(__file__), "ignore_list.txt"), "a") as file:
    file.write(text)
