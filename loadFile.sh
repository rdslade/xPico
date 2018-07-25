ip=$1
file=$2
location=$3
loadType = $4

echo "Loading " $loadType " files"

echo "IP addr: " $ip
echo "File: " $file
echo "Location: " $location

tftp -i $ip put $file $location
if [ $? -eq 0 ]
then
  echo "SUCCESS"
else
  echo "FAIL"
fi

sleep 2
