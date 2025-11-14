Differences Between Hash Algorithms
Each hash algorithm has different strengths and weaknesses for finding duplicate or similar images:
pHash (Perceptual Hash) is considered the most balanced and widely used algorithm, offering good accuracy while being relatively fast. It uses Discrete Cosine Transform (DCT) to convert images to frequency domains, making it robust against resizing, minor color adjustments, and compression artifacts.
Average Hash is the simplest and fastest algorithm. It works by resizing the image to a small square, calculating the average pixel value, and creating a binary hash based on whether pixels are above or below that average. It's great for exact duplicates but less effective for altered images.
dHash (Difference Hash) computes differences between adjacent pixels rather than absolute values. This makes it particularly good at detecting structural elements and edges, making it excellent for detecting images with brightness or contrast changes.
Wavelet Hash (whash-haar) is the most sophisticated of these algorithms, using wavelet decomposition to analyze images at different scales. It's best for detecting complex similarities between significantly modified images, though it's also the most computationally expensive.
Best Two-Stage Combinations
For a two-stage approach, here are the best combinations:

pHash + dHash: This is likely the best general-purpose combination

pHash provides a good baseline for similarity
dHash complements by focusing on structural changes and edge differences
Both are relatively efficient while covering different types of modifications


Average Hash + pHash:

Fast initial screening with Average Hash
More accurate refinement with pHash
Good for large collections where performance matters


pHash + Wavelet Hash:

For maximum accuracy when performance is less critical
pHash catches most duplicates efficiently
Wavelet Hash refines results for heavily modified images


Average Hash + dHash:

Fastest combination with decent accuracy
Good complementary coverage of different image characteristics



For your current threshold values (0.985 for exact, 0.95 for variant, 0.92 for similar), pHash as primary and dHash as secondary would likely give you the best balance of accuracy and performance. This combination is particularly good at detecting both structural and perceptual similarities across different types of image modifications.