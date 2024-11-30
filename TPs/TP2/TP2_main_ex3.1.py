import cv2
import numpy as np
from math import *
from TPs.TP2 import paths
import matplotlib.pyplot as plt
import time


IMAGE_PATH = paths.IMAGE_PATH


""" Hough parameters """
DELTA_R = 1
DELTA_C = 1
DELTA_RAD = 1
MIN_R = 0
MIN_C = 0
MIN_RAD = 1

N_CIRCLES = 4
FILTER_EDGES_THRESHOLD = 0.1
LOCAL_MAX_KERNEL_SIZE = 7 # Size of the kernel (cube) that avoid multiple similar circles (same center and radius)


def main():
    # Load the image
    image = cv2.imread(IMAGE_PATH) #cv2.IMREAD_GRAYSCALE

    # Get the edges image
    edges_image = get_edges_image(image, threshold_ratio=FILTER_EDGES_THRESHOLD)

    display_image(edges_image)
    start_time = time.time()  # Record the start time

    image_gradient_direction = sobel_filter(image)

    circles_coords = hough_method(edges_image, image_gradient_direction)
    print("circles_coords : ", circles_coords)

    end_time = time.time()  # Record the end time
    execution_time = end_time - start_time  # Calculate the execution time
    print(f"Execution time: {execution_time:.2f} seconds")

    draw_circles(image, circles_coords)
    display_image(image)



def sobel_filter(image):
    # Ensure the input image is grayscale
    if len(image.shape) == 3:  # Check if the image has 3 channels (color)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply the Sobel filter in the x and y directions
    sobel_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)

    # Compute gradient magnitude and direction
    gradient_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
    gradient_direction = np.arctan2(sobel_y, sobel_x)  # In radians

    # Normalize Sobel outputs for visualization (scale to 0-255)
    sobel_x_normalized = cv2.convertScaleAbs(sobel_x)
    sobel_y_normalized = cv2.convertScaleAbs(sobel_y)
    gradient_magnitude_normalized = cv2.convertScaleAbs(gradient_magnitude)

    # Display the results
    titles = ['Original Image', 'Sobel X', 'Sobel Y', 'Gradient Magnitude', 'Gradient Direction']
    images = [image, sobel_x_normalized, sobel_y_normalized, gradient_magnitude_normalized, gradient_direction]

    plt.figure(figsize=(8, 10))

    for i in range(len(images)):
        plt.subplot(3, 2, i + 1)
        if i == len(images) - 1:  # Gradient direction uses a colormap for angles
            plt.imshow(images[i], cmap='hsv')  # Hue for direction
        else:
            plt.imshow(images[i], cmap='gray')  # Grayscale for other visualizations
        plt.title(titles[i])
        plt.axis('off')

    plt.tight_layout()
    plt.show()

    return gradient_direction


def display_image(image):
    # Display the edges
    cv2.imshow('Image', image)

    # Wait for a key press and close the window
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def get_edges_image(image, gaussian_ksize=(5, 5), threshold_ratio=0.1):
    #Apply Gaussian blur to reduce noise (optional but recommended)
    blurred_image = cv2.GaussianBlur(image, gaussian_ksize, 0)

    # Apply Sobel filters to compute the gradients in the x and y directions
    sobel_x = cv2.Sobel(blurred_image, cv2.CV_64F, 1, 0, ksize=3)  # Gradient in x-direction
    sobel_y = cv2.Sobel(blurred_image, cv2.CV_64F, 0, 1, ksize=3)  # Gradient in y-direction

    # Compute the gradient magnitude
    magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)

    # Normalize the magnitude to the range [0, 255] for better visualization
    magnitude_normalized = np.uint8(np.clip(magnitude / np.max(magnitude) * 255, 0, 255))

    # Threshold to create the final edge image (binary)
    _, edges_image = cv2.threshold(magnitude_normalized, threshold_ratio * 255, 255, cv2.THRESH_BINARY)

    return edges_image


def get_edges_coordinates(edges_image):
    # Ensure the input is a 2D binary image (single-channel)
    if len(edges_image.shape) != 2 or edges_image.shape[2] != 1:
        edges_image = cv2.cvtColor(edges_image, cv2.COLOR_BGR2GRAY)

    # Find the coordinates of edge pixels (non-zero pixels in the binary image)
    edge_coordinates = cv2.findNonZero(edges_image)

    # Convert the coordinates to a list of tuples (x, y)
    edge_coordinates = [(point[0][0], point[0][1]) for point in edge_coordinates]

    return edge_coordinates


def populate_accumulator(edges_image, image_gradient_direction):
    # Get the dimensions of the image
    image_height, image_width = edges_image.shape[:2]

    r_max = image_height - 1
    c_max = image_width - 1

    n_c = floor(((c_max - MIN_C) / DELTA_C) + 1)  # The number of column discretize
    n_r = floor(((r_max - MIN_R) / DELTA_R) + 1)  # The number of rows discretize
    diagonal = np.sqrt(image_width ** 2 + image_height ** 2)
    n_rad = floor(((diagonal - MIN_RAD) / DELTA_R) + 1)

    print("n_r_values : ", n_r)
    print("n_c_values : ", n_c)
    print("n_rad_values : ", n_rad)
    print("diagonal : ", diagonal)
    accumulator = np.zeros((n_c, n_r, n_rad))

    edge_coordinates = get_edges_coordinates(edges_image)

    for edge in edge_coordinates:
        edge_x, edge_y = edge

        # Gradient direction at the edge point (opposite direction for inward normal)
        theta = image_gradient_direction[edge_y, edge_x] + np.pi  # Reverse direction

        for radius in range(MIN_RAD, int(diagonal), 1):
            # Compute possible circle center
            center_x = round(edge_x + radius * np.cos(theta))  # Center x-coordinate
            center_y = round(edge_y + radius * np.sin(theta))  # Center y-coordinate

            # Update the accumulator if the circle center is within the image
            if 0 <= center_x < image_width and 0 <= center_y < image_height:
                acc_c_idx = int((center_x - MIN_C) / DELTA_C)
                acc_r_idx = int((center_y - MIN_R) / DELTA_R)
                acc_rad_idx = int((radius - MIN_RAD) / DELTA_RAD)
                accumulator[acc_c_idx][acc_r_idx][acc_rad_idx] += (1 / (2 * np.pi * radius))

    return accumulator


def get_local_maximum(accumulator):
    n_c, n_r, n_rad = accumulator.shape

    padding = int(LOCAL_MAX_KERNEL_SIZE / 2)
    kernel = list(range(-padding, padding + 1))

    # Initialize an empty list to store the coordinates of local maxima
    local_maxima_coords = []

    # Loop through each element in the 3D array, avoiding the borders
    for x in range(padding, n_c - padding):
        for y in range(padding, n_r - padding):
            for z in range(padding, n_rad - padding):
                # Get the current value
                current_value = accumulator[x, y, z]

                # Flag to check if this is a local maximum
                is_local_maximum = True

                # Loop through the neighboring cells
                for dx in kernel:
                    for dy in kernel:
                        for dz in kernel:
                            if dx == 0 and dy == 0 and dz == 0:
                                continue  # Skip the current cell itself

                            # Compare with neighboring cell
                            neighbor_value = accumulator[x + dx, y + dy, z + dz]
                            if neighbor_value >= current_value:
                                is_local_maximum = False
                                break  # Stop checking neighbors if one is greater or equal
                        if not is_local_maximum:
                            break
                    if not is_local_maximum:
                        break

                # If it's a local maximum, save its coordinates
                if is_local_maximum:
                    acc_value = accumulator[x, y, z]
                    local_maxima_coords.append((x, y, z, acc_value))

    # Sort the local_maxima_coords in descending order based on the accumulator value
    sorted_local_maxima_coords = sorted(local_maxima_coords, key=lambda x: x[3], reverse=True)
    sorted_local_maxima_coords = sorted_local_maxima_coords[:N_CIRCLES]

    return sorted_local_maxima_coords


def draw_circles(original_image, sorted_local_maxima_coords):
    color = (0, 255, 0)
    thickness = 1

    n_circles = len(sorted_local_maxima_coords)

    # Drawing circles
    for i in range(n_circles):
        x_idx, y_idx, radius_idx = sorted_local_maxima_coords[i][:3]
        x = int((x_idx * DELTA_C) + MIN_C)
        y = int((y_idx * DELTA_R) + MIN_R)
        radius = int((radius_idx * DELTA_RAD) + MIN_RAD)

        cv2.circle(original_image, (x, y), radius, color, thickness)


def hough_method(edges_image, image_gradient_direction):
    accumulator = populate_accumulator(edges_image, image_gradient_direction)

    sorted_local_maxima_coords = get_local_maximum(accumulator)

    return sorted_local_maxima_coords


def compute_pixels_distance(p1x, p1y, p2x, p2y):
    return sqrt((p2x - p1x) ** 2 + (p2y - p1y) ** 2)


if __name__ == '__main__':
   main()