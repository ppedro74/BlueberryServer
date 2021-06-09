        #pixmax = max(pixels)
        #pixels = [x / pixmax for x in pixels]
        #pixels = [map_value(p, MINTEMP, MAXTEMP, 0, 1) for p in pixels]
        # bicubic interpolation of 8x8 grid to make a 32x32 grid
        #bicubic = griddata(points, pixels, (grid_x, grid_y), method='cubic')
        #image = np.array(bicubic)
        #image = np.reshape(image, (32, 32))
        #print(image)
        #plt.imsave('color_img.jpg', image)
        #img = cv2.imread("color_img.jpg", cv2.IMREAD_GRAYSCALE)
        #image2 = cv2.normalize(temps, None, 0, 255, cv2.NORM_MINMAX)



    #value = 0xFFFE
    #l1 = value.to_bytes(2, "little")
    #b1 = value.to_bytes(2, "big")
    #l2 = bytes([value & 0xFF, value >> 8 & 0xFF])
    #b2 = bytes([value >> 8 & 0xFF, value & 0xFF])


    def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))

def map_value(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def plotdata():
    # preallocating variables
    norm_pix = []
    cal_vec = []
    kk = 0
    cal_size = 2
    cal_pix = []
    time_prev = time.time() # time for analyzing time between plot updates
    for ix in range(3):
        # calibration procedure #
        if kk == 0:
                print("Sensor should have clear path to calibrate against environment")
                graph = plt.imshow(np.reshape(np.repeat(0,64),(8,8)),cmap=plt.cm.hot,interpolation='lanczos')
                plt.colorbar()
                plt.clim(1,8) # can set these limits to desired range or min/max of current sensor reading
                plt.draw()

        #norm_pix = sensor.readPixels()
        norm_pix = np.loadtxt("assets\\data\\pixels{0}.txt".format(ix), dtype=float)

        if kk < cal_size + 1:
                kk+=1
        if kk == 1:
                cal_vec = norm_pix
                continue
        elif kk <= cal_size:
                for xx in range(0,len(norm_pix)):
                        cal_vec[xx]+=norm_pix[xx]
                        if kk == cal_size:
                                cal_vec[xx] = cal_vec[xx] / cal_size
                continue
        else:
                [cal_pix.append(norm_pix[x] - cal_vec[x]) for x in range(0,len(norm_pix))]
                if min(cal_pix) < 0:
                        for y in range(0,len(cal_pix)):
                                cal_pix[y]+=abs(min(cal_pix))

        # Moving Pixel Plot #
        print(np.reshape(cal_pix,(8,8))) # this helps view the output to ensure the plot is correct
        graph.set_data(np.reshape(cal_pix,(8,8))) # updates heat map in 'real-time'
        plt.draw() # plots updated heat map
        cal_pix = [] # off-load variable for next reading
        print(time.time() - time_prev) # prints out time between plot updates
        time_prev = time.time()
    plt.show()


def test2(pixels):
    # Read pixels, convert them to values between 0 and 1, map them to an 8x8
    # grid
    pixmax = max(pixels)
    pixels = [x / pixmax for x in pixels]
    points = [(math.floor(ix / 8), (ix % 8)) for ix in range(0, 64)]
    grid_x, grid_y = np.mgrid[0:7:32j, 0:7:32j]

    # bicubic interpolation of 8x8 grid to make a 32x32 grid
    bicubic = griddata(points, pixels, (grid_x, grid_y), method='cubic')
    image = np.array(bicubic)
    image = np.reshape(image, (32, 32))
    print(image)
    #plt.imsave('color_img.jpg', image)
    #buf = io.BytesIO()
    #plt.savefig(buf, format='png')
    #buf.seek(0)
    #im = Image.open(buf)
    #im.show()
    #buf.close()
    im = Image.fromarray(image.astype(np.uint16), mode='L')
    im = im.resize((140, 140))
    im.show()

def createSamples(controller, number_of_samples):
    for ix in range(number_of_samples):
        pixels = np.asarray(controller.readPixels())
        
        np.save("pixels{0}.npy".format(ix), pixels) 
        np.savetxt("pixels{0}.txt".format(ix), pixels, fmt='%f')

        print(pixels)
        pixels2 = np.load("pixels{0}.npy".format(ix))
        pixels2 = np.loadtxt("pixels{0}.txt".format(ix), dtype=float)

        if not np.array_equal(pixels, pixels2):
            print("error")
        print("sleep 2 seconds...")
        time.sleep(2)