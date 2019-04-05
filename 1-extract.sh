destdir="1-ca-shapefiles"
rm -rf $destdir
mkdir $destdir
for i in *.zip; do
    unzip -o "$i" -d $destdir
done
