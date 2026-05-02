FROM node:22-alpine
WORKDIR /web
COPY web/package.json /web/package.json
RUN npm install
COPY web /web
EXPOSE 5173
CMD ["npm", "run", "dev"]
