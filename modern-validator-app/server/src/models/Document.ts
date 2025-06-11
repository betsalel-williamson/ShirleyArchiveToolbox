// server/src/models/Document.ts
import { DataTypes, Model, Optional } from 'sequelize';
import { sequelize } from '../database.js';

interface DocumentAttributes {
  id: number;
  filename: string;
  imageSource: string;
  status: 'source' | 'in_progress' | 'validated';
  sourceData: object;
  currentData: object;
}

interface DocumentCreationAttributes extends Optional<DocumentAttributes, 'id'> {}

class Document extends Model<DocumentAttributes, DocumentCreationAttributes> implements DocumentAttributes {
  public id!: number;
  public filename!: string;
  public imageSource!: string;
  public status!: 'source' | 'in_progress' | 'validated';
  public sourceData!: object;
  public currentData!: object;
}

Document.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    filename: {
      type: DataTypes.STRING,
      allowNull: false,
      unique: true,
    },
    imageSource: {
      type: DataTypes.STRING,
      allowNull: false,
    },
    status: {
      type: DataTypes.ENUM('source', 'in_progress', 'validated'),
      defaultValue: 'source',
      allowNull: false,
    },
    sourceData: {
      type: DataTypes.JSON,
      allowNull: false,
    },
    currentData: {
      type: DataTypes.JSON,
      allowNull: false,
    },
  },
  {
    sequelize,
    tableName: 'documents',
  }
);

export default Document;
