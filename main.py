#PySimpleGUI, numpy, scipy, and matplotlib
#Python version 3.11.6 64 bit
#pip install pysimplegui                #needed
#pip install pillow                     #needed
#python -m pip install -U matplotlib    #needed

TYPES = {
'1':  1,  #8-bit unsigned integer.
'2' : 1,  # 8-bit byte that contains a 7-bit ASCII code; the last bytemust be NUL (binary zero).
'3' : 2,  #16-bit (2-byte) unsigned integer.
'4' : 4,  #32-bit (4-byte) unsigned integer
'5' : 8,  #Two LONGs: the first represents the numerator of afraction; the second, the denominator
'6' : 1,  #An 8-bit signed (twos-complement) integer.
'7' : 1,  #An 8-bit byte that may contain anything, depending onthe definition of the field.
'8' : 2,  #A 16-bit (2-byte) signed (twos-complement) integer.
'9' : 4,  #A 32-bit (4-byte) signed (twos-complement) integer
'10': 8,  #two signed longs, numerator and denominator
'11': 4,  #FLOAT Single precision (4-byte) IEEE format.
'12': 8  #DOUBLE Double precision (8-byte) IEEE format
}


import PySimpleGUI as sg
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import io



def read_image(file_name):
    # Open the TIFF file (https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf)
    with open(file_name, 'rb') as file:

        #Read Tiff file header
        tif_byte_order = file.read(2).decode('ascii') #Gives endian order
        print(f"Byte Order: {tif_byte_order}")

        if tif_byte_order == 'MM':
            tif_byte_order = 'big'
        elif tif_byte_order == 'II':
            tif_byte_order = 'little'
            
        #Get Header ID (always 42)
        tif_id_42 = int.from_bytes(file.read(2), byteorder=tif_byte_order)
        #Get offset for first IFD
        tif_first_IFD_offset = int.from_bytes(file.read(4), byteorder=tif_byte_order)
        print(f"1st IFD Offset: {tif_first_IFD_offset}")

        #Go to first IFD offset location
        file.seek(tif_first_IFD_offset)

        #Get number of directories 
        number_of_directory_entries = int.from_bytes(file.read(2), byteorder=tif_byte_order)
        #print(f"Number of Directory Entries: {number_of_directory_entries}")

        #This data points to the image data
        strip_offsets = []
        strip_byte_counts = []

        # Define the dimensions of the image
        width = 0
        height = 0

        for i in range(number_of_directory_entries):
            #Directory Entry i
            entry_tag = int.from_bytes(file.read(2), byteorder=tif_byte_order)
            entry_type = int.from_bytes(file.read(2), byteorder=tif_byte_order)
            entry_count = int.from_bytes(file.read(4), byteorder=tif_byte_order)
            entry_value = []

            #Remember where we are
            current_position = file.tell()

            #Determine if the values chunk contains a value or an offset then perform read
            if (TYPES[str(entry_type)] * entry_count) <= 4: #Contains a value
                entry_value.append( int.from_bytes(file.read(TYPES[str(entry_type)] * entry_count), byteorder=tif_byte_order))
                file.read(4 - (TYPES[str(entry_type)] * entry_count))
            else: #Contains an offset
                value_offset = int.from_bytes(file.read(4), byteorder=tif_byte_order)
                file.seek(value_offset)
                for j in range(entry_count):
                    entry_value.append(int.from_bytes(file.read(TYPES[str(entry_type)]), byteorder=tif_byte_order))
                file.seek(current_position + 4)

            
            #Get Important Image information. There are many other tags but these are the most important  
            match entry_tag:
                case 256:
                    width = entry_value[0]
                case 257:
                    height = entry_value[0]
                #This specifies the position (offset) of the start of the image data, the rgb values. This can be a single offset or a list of offsets
                case 273:
                    strip_offsets = entry_value
                #This specifies the quanitity of bytes of image data per offset
                case 279:
                    strip_byte_counts = entry_value

            print(f"\nDirectory Entry {i}")
            print(f"Tag: {entry_tag}")
            print(f"Type: {entry_type}")
            print(f"Count: {entry_count}")
            print(f"Value: {entry_value}")

        #Initialize rgb_values list (holds lists of [r,g,b] values)
        rgb_values = []

        #The method of file reading flips the image in a weird way. Swapping dimensions then transposing the image fixes this
        temp = width
        width = height
        height = temp

        #IMPORTANT
        #This nested for loop reads the image starting at the top right row and working left, then proceeding to the right of the next row and so on
        #Each width# of iterations of the inner loop generates one "row" in reverse order (from right to left)
        #Due to the way strip_offset works and the corresponding count for tag 273, a nested for loop is necessary.

        #Go to the image data
        for i in range(len(strip_offsets)):
            file.seek(strip_offsets[i])
            for j in range(0, strip_byte_counts[i],3):
                rgb_pixel = []
                rgb_pixel.append(int.from_bytes(file.read(1), byteorder=tif_byte_order))
                rgb_pixel.append(int.from_bytes(file.read(1), byteorder=tif_byte_order))
                rgb_pixel.append(int.from_bytes(file.read(1), byteorder=tif_byte_order))              
                rgb_values.append(rgb_pixel)

        #Image Data Location/Quanitity info
        #print("\nStrip info")
        #print(f"Offsets: {strip_offsets}")
        #print(f"Byte Counts: {strip_byte_counts}")

        #Initialize image in the form of a matrix that holds lists [r,g,b] in the same order as the actual image
        image_matrix = []

        #Transform the 1D array of lists { [r,g,b], [r,g,b], ... }, to a 2D matrix
        counter = 0
        for i in range(width):
            image_matrix.append([])
            for j in range(height):
                image_matrix[i].append(rgb_values[counter])
                counter += 1

        # Create a new image with a white background (this is the actual image representation that will be viewed)
        im = Image.new("RGB", (width, height), "white")

        # Access the new images pixel data
        pixels = im.load()

        # Draw the rgb values from image_matrix
        for x in range(width):
            for y in range(height):
                pixels[x, y] = (image_matrix[x][y][0], image_matrix[x][y][1], image_matrix[x][y][2])  # RGB value for red

        #Transpose (this is do the the way the data is set up during the read)
        im = im.transpose(method = Image.Transpose.ROTATE_270)

    return im

# Create a placeholder image
placeholder_text = "Image will appear here"
placeholder_image = Image.new("RGB", (300, 200), (44,40,37))
draw = ImageDraw.Draw(placeholder_image)
draw.text((50, 100), placeholder_text, fill='white', font_size=20)

# Convert the placeholder image to bytes
placeholder_bytes = io.BytesIO()
placeholder_image.save(placeholder_bytes, format='PNG')
placeholder_bytes = placeholder_bytes.getvalue()

#Setup GUI
sg.theme('DarkAmber')

#Main Window Layout
main_layout = [
    [sg.Button('Open File'), sg.Button('Exit')],
    [sg.Image(key='-IMAGE-', size=(704,576), pad=(0,0), expand_x=True, expand_y=True)]
]

# Create the Main Window
main_window = sg.Window('Assignment 1 Question 2', main_layout, finalize=True, resizable=False, size=(704,650))

#Set the place holder image into the image
main_window['-IMAGE-'].update(data=placeholder_bytes)

# Render Menu
while True:
    event, values = main_window.read()
    match event:
        #Render "Open File" dialog box
        case 'Open File':
            open_layout = [
                [sg.Text('Enter File Path: '), sg.InputText(default_text="test samples/Q2/")],
                [sg.Button('Submit'), sg.Text("Image failed to load!", key="-ERROR_TEXT-", visible = False)],
                [sg.Text("or Select An Image: ")],
                [sg.Button('image1.tif', pad=(5,0)),sg.Button('image2.tif'),sg.Button('image3.tif'), sg.Button('Cancel', pad=((100, 0), 0))]
            ]
            open_file_window = sg.Window('Open File', open_layout, finalize=True, size=(400, 125), keep_on_top=True)
            while True:
                open_event, values = open_file_window.read()
                match open_event:

                    case 'Submit':
                        try:
                            im = read_image(values[0])
                            image_bytes = io.BytesIO()
                            im.save(image_bytes, format='PNG')
                            image_bytes = image_bytes.getvalue()
                            main_window['-IMAGE-'].update(data=image_bytes)
                            break
                        except IOError as e:
                            open_file_window['-ERROR_TEXT-'].update(visible=True)                    
                    case 'Cancel':
                        break
                    case sg.WIN_CLOSED:                        
                        break
                    #Enable shortcut buttons
                    case 'image1.tif':
                        im = read_image("test samples/Q2/image1.tif")
                        image_bytes = io.BytesIO()
                        im.save(image_bytes, format='PNG')
                        image_bytes = image_bytes.getvalue()
                        main_window['-IMAGE-'].update(data=image_bytes)
                        break
                    case 'image2.tif':
                        im = read_image("test samples/Q2/image2.tif")
                        image_bytes = io.BytesIO()
                        im.save(image_bytes, format='PNG')
                        image_bytes = image_bytes.getvalue()
                        main_window['-IMAGE-'].update(data=image_bytes)
                        break
                    case 'image3.tif':
                        im = read_image("test samples/Q2/image3.tif")
                        image_bytes = io.BytesIO()
                        im.save(image_bytes, format='PNG')
                        image_bytes = image_bytes.getvalue()
                        main_window['-IMAGE-'].update(data=image_bytes)
                        break
            open_file_window.close()
        case 'Exit':
            break
        case sg.WIN_CLOSED:
            break
