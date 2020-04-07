import os
import shutil
import requests
import cv2 as cv

folder = 'tmp'

def download_image(url, name=None):
    if not name:
        name = url.split('/')[-1]
    
    path = os.path.join(folder, name + '.jpg')

    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(path, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)    

        return path  

def mix_images(img1, img2, alpha=0.5):
    img1 = download_image(img1)
    img2 = download_image(img2)

    src1 = cv.imread(cv.samples.findFile(img1))
    src2 = cv.imread(cv.samples.findFile(img2))

    # [load]
    if src1 is None:
        print("Error loading src1")
        exit(-1)
    elif src2 is None:
        print("Error loading src2")
        exit(-1)
    # [blend_images]
    beta = (1.0 - alpha)
    dst = cv.addWeighted(src1, alpha, src2, beta, 0.0)
    # [blend_images]
    # [display]
    cv.imshow('dst', dst)
    cv.waitKey(0)
    # [display]
    cv.destroyAllWindows()