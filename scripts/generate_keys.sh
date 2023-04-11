#!/bin/sh
# Some constants
readonly CERT_DIR=certs
readonly CERT_FILENAME=.cert.pem
readonly KEY_FILENAME=.key.pem

# We all need help sometimes
Help()
{
    # Display Help
    echo "Generate new TLS certificates and keys and report LFDI number for Xcel registration"
    echo
    echo "Syntax: $0"
    echo "options:"
    echo "  -p     Print LFDI string"
    echo "  -h     Print this Help."
    echo
}

generate_new_keys()
{
    # Generate new TLS1.2 keys for Xcel meter
    echo "Generating new keys!"
    openssl req -x509 -nodes -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -keyout ${CERT_DIR}/${KEY_FILENAME} -out ${CERT_DIR}/${CERT_FILENAME} -sha256 -days 1094 -subj '/CN=MeterReaderHanClient' -addext "certificatePolicies = critical,1.3.6.1.4.1.40732.2.2" -addext "keyUsage = critical,digitalSignature"
}

print_LFDI()
{
    echo "The following string of numbers should be used as your LFDI value on the Xcel website:"
    # Print out the LFDI string for registration
    openssl x509 -noout -fingerprint -SHA256 -inform pem -in ${CERT_DIR}/${CERT_FILENAME} | sed -e 's/://g' -e 's/SHA256 Fingerprint=//g' | cut -c1-40
}

while getopts "ph" option; do
    case "${option}" in
        p) # Print LFDI
            print_LFDI
            exit;;
        h | *)
            Help
            exit;;
    esac
done

if [ -f "${CERT_DIR}/${CERT_FILENAME}" ] && [ -f "${CERT_DIR}/${KEY_FILENAME}" ]; then
    echo "Looks like you have already generated your cert and key files."
    read -p "Would you like to overwrite your existing credentials? [Y/n] "
    if [ -z "${REPLY}" ]; then REPLY="Y"; fi
    if [ ${REPLY^^} = "Y" ]; then
        generate_new_keys
        print_LFDI
    fi
    exit
fi

if [ ! -d "${CERT_DIR}" ]; then
    echo "${CERT_DIR} DOES NOT exist, creating now."
    mkdir -p ${CERT_DIR}
fi

generate_new_keys
print_LFDI
